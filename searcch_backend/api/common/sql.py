
import sqlalchemy
import datetime
import logging
import json
import sys
import base64

LOG = logging.getLogger(__name__)

from searcch_backend.api.app import db
from searcch_backend.models import model

conv_type_map = {
    datetime.datetime: {
        "parse": datetime.datetime.fromisoformat,
        "valid": str,
        "typeinfo": "isoformat str"
    },
    bytes: {
        "parse": lambda x: base64.b64decode(x),
        "serialize": lambda x: base64.b64encode(x).decode("utf-8"),
        "valid": str,
        "typeinfo": str
    }
}

class CustomJSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, bytes):
            return base64.b64encode(o).decode("utf-8")
        return json.JSONEncoder.default(self, o)

def get_primary_key_for_class(model_class):
    for k in model_class.__mapper__.column_attrs.keys():
        # Skip primary keys or foreign keys.
        colprop = getattr(model_class,k).property.columns[0]
        if colprop.primary_key:
            return k
    return None

def artifact_diff(session, curator, artifact, obj1, obj2, update=True, path="",
                  skip_tsv=True):
    if not isinstance(artifact,model.Artifact):
        raise TypeError("artifact is not an Artifact")
    if type(obj1) != type(obj2):
        raise TypeError("object type mismatch (%r,%r)" % (type(obj1),type(obj2)))
    if not isinstance(obj1,db.Model):
        raise TypeError("object not part of the model")

    curations = []
    obj_class = obj1.__class__
    curator_id = curator.id if curator else None

    #
    # Be warned -- if `obj2` has any unset nullable=False fields, and if a
    # `session.refresh` is triggered, sqlalchemy will fail to load the object.
    # This is a useful canary-in-the-coal-mine for now.
    #
    try:
        LOG.debug("diffing class %r and class %r" % (obj1.__class__.__name__,obj2.__class__.__name__))
    except:
        pass
    LOG.debug("diffing %r and %r" % (repr(obj1),repr(obj2)))

    # Diff the non-primary and non-foreign-key fields.
    user_ro_fields = getattr(obj_class,"__user_ro_fields__",{})
    for k in obj_class.__mapper__.column_attrs.keys():
        if skip_tsv and k.endswith("_tsv"):
            continue

        obj1_val = getattr(obj1,k,None)
        obj2_val = getattr(obj2,k,None)

        # Primary keys and foreign keys are not allowed to change.
        colprop = getattr(obj_class,k).property.columns[0]
        if colprop.primary_key or colprop.foreign_keys:
            if obj2_val is not None and obj1_val != obj2_val:
                raise ValueError("not allowed to modify primary/foreign key %r" % (k,))
            continue

        # If obj1 and obj2 both came from the DB or from object_from_json, we
        # can assume their types and value constraints are correct.  So we just
        # have to test equivalence.
        if obj2_val != obj1_val:
            if k in user_ro_fields:
                raise ValueError("not allowed to modify field %s" % (k,))
            LOG.debug("field %s diff: '%r' != '%r'" % (k,repr(obj1_val),repr(obj2_val)))
            opdata = { "obj": obj_class.__name__,
                       "op": "set",
                       "data": { "field": k, "value": obj2_val } }
            if path:
                opdata["path"] = path
            curation = model.ArtifactCuration(
                artifact_id=artifact.id,time=datetime.datetime.now(),
                opdata=json.dumps(opdata, cls=CustomJSONEncoder),curator_id=curator_id)
            curations.append(curation)
            if update:
                setattr(obj1,k,obj2_val)

    # Diff relationships.  We match on primary key (nearly always ID in our
    # schema).  If the primary_key does not exist, this is a new object that is
    # not in the first.
    user_ro_relationships = getattr(obj_class,"__user_ro_relationships__",{})
    user_skip_relationships = getattr(obj_class,"__user_skip_relationships__",{})
    for k in obj_class.__mapper__.relationships.keys():
        # We don't care if user does or does not supply these.
        if k in user_skip_relationships or k in user_ro_relationships:
            continue

        relprop = getattr(obj_class,k).property
        if len(relprop.local_columns) > 1:
            raise TypeError("cannot handle relationship with multiple foreign keys")

        (lcc,) = relprop.local_columns

        if False and lcc.foreign_keys:
            # This is a relationship through a foreign key we store in this
            # table, into another table.  We don't allow editing of these keys,
            # so skip it.
            continue

        # We must delete referenced objects if we cannot nullify their foreign
        # keys into this object.
        delete_referenced_objects = False
        for rsk in relprop.remote_side:
            for fk in rsk.foreign_keys:
                # If the foreign key is not nullable, AND
                # If it points into obj_class's table
                if not rsk.nullable and obj_class.__mapper__.local_table.name == fk.column.table.fullname:
                    LOG.debug("dro: %r %r %r" % (rsk,obj_class.__mapper__.local_table.name,fk.column.table.fullname))
                    delete_referenced_objects = True
                    break

        # Otherwise, this is a relationship into another table via a key in our
        # table, probably our primary key.  We check via primary key of the
        # item(s) if any have been removed, added, or modified.  In particular,
        # we want to see if the objects in obj2[k] are in obj1[k], and
        # if so, if they differ... etc.
        deletes = []
        adds = []
        obj1_rval = getattr(obj1,k)
        obj2_rval = getattr(obj2,k)

        # Handle both one-to-one and one-to-many relations in the same code
        # below.
        if not relprop.uselist:
            if obj1_rval:
                obj1_rval = [ obj1_rval ]
            else:
                obj1_rval = []
            if obj2_rval:
                obj2_rval = [ obj2_rval ]
            else:
                obj2_rval = []

        foreign_class = relprop.argument()
        foreign_primary_key = get_primary_key_for_class(foreign_class)
        obj1_rval_pk_map = {}
        obj2_rval_pk_map = {}

        # Construct maps for easy assessment of addition/deletion.
        for i in range(0,len(obj1_rval)):
            x = obj1_rval[i]
            val = getattr(x,foreign_primary_key,None)
            if val is not None:
                obj1_rval_pk_map[val] = (i,x)
            else:
                raise ValueError("original object relation pkey values must not be None (class %r, relation %r)"
                                 % (obj_class.__name__,k))
        # Setup modified map; journal additions.
        for i in range(0,len(obj2_rval)):
            x = obj2_rval[i]
            val = None
            LOG.debug("trying to read %s.%s",x.__class__.__name__,foreign_primary_key)
            val = getattr(x,foreign_primary_key,None)
            #except:
            #    LOG.debug("would have been an exception (%r/%r)",path,k)
            #    LOG.exception(sys.exc_info()[1])
            if val is not None:
                if val not in obj1_rval_pk_map:
                    if not getattr(foreign_class,"__object_from_json_allow_pk__",False):
                        raise ValueError("cannot set primary key to value %r not present in original object" % (val,))
                    LOG.debug("adding relation %r",k)
                    #session.add(x)
                    #LOG.debug("added relation %r item: %r" % (k,x))
                    adds.append(x)
                obj2_rval_pk_map[val] = (i,x)
            else:
                LOG.debug("adding relation %r",k)
                #session.add(x)
                #LOG.debug("added relation %r item: %r" % (k,x))
                adds.append(x)
        # Look for deletions.
        for (o1k,o1v) in obj1_rval_pk_map.items():
            if not o1k in obj2_rval_pk_map:
                LOG.debug("deleted relation %r item: %r" % (o1k,o1v,))
                deletes.append(o1v)

        LOG.debug("%r/%r orig (%r) new (%r)",path,k,
                  list(obj1_rval_pk_map.keys()),
                  list(obj2_rval_pk_map.keys()))

        # Trawl for possible modifications.
        for (o1k,(o1i,o1v)) in obj1_rval_pk_map.items():
            if not o1k in obj2_rval_pk_map:
                # NB: this just happens because we don't modify the maps as we
                # journal additions/deletions; so ignore.
                continue
            # Finally, recurse:
            (o2i,o2v) = obj2_rval_pk_map[o1k]
            rcurations = artifact_diff(session,curator,artifact,o1v,o2v,update=update,path=path+"."+k)
            if rcurations:
                curations.extend(rcurations)

        # Make the add/deletes live.
        deletes.reverse()
        if deletes and delete_referenced_objects:
            LOG.debug("will delete referenced objects of relation %s.%s",obj_class.__name__,k)

        for (i,x) in deletes:
            acj = json.dumps(
                { "obj": foreign_class.__name__,"op": "del",
                "data":{ "field":k,"value": object_to_json(x) } },
                separators=(',',':'))
            ac = model.ArtifactCuration(
                artifact_id=artifact.id,time=datetime.datetime.now(),
                opdata=acj,curator_id=curator_id)
            curations.append(ac)
            if delete_referenced_objects:
                LOG.debug("deleting referenced object %r",x)
                if update:
                    session.delete(x)
            if not relprop.uselist:
                if update:
                    setattr(obj1,k,None)
            else:
                if update:
                    del getattr(obj1,k)[i]
        for x in adds:
            acj = json.dumps(
                { "obj": foreign_class.__name__,"op": "add",
                  "data":{ "field":k,"value": object_to_json(x) } },
                separators=(',',':'))
            ac = model.ArtifactCuration(
                artifact_id=artifact.id,time=datetime.datetime.now(),
                opdata=acj,curator_id=curator_id)
            curations.append(ac)
            if not relprop.uselist:
                if update:
                    setattr(obj1,k,x)
            else:
                if update:
                    getattr(obj1,k).append(x)
            LOG.debug("added relation %r item: %r" % (k,x))

    return curations

def artifact_diff_by_value(session, curator, artifact, obj1, obj2, update=True,
                           path="", skip_ids=True, skip_tsv=True):
    if not isinstance(artifact,model.Artifact):
        raise TypeError("artifact is not an Artifact")
    if type(obj1) != type(obj2):
        raise TypeError("object type mismatch (%r,%r)" % (type(obj1),type(obj2)))
    if not isinstance(obj1,db.Model):
        raise TypeError("object not part of the model")

    curations = []
    obj_class = obj1.__class__
    curator_id = curator.id if curator else None
    curation_time = datetime.datetime.now() if curator else None

    #
    # Be warned -- if `obj2` has any unset nullable=False fields, and if a
    # `session.refresh` is triggered, sqlalchemy will fail to load the object.
    # This is a useful canary-in-the-coal-mine for now.
    #
    try:
        LOG.debug("diff_by_value: class %r and class %r",
                  obj1.__class__.__name__,obj2.__class__.__name__)
    except:
        pass
    LOG.debug("diff_by_value: %r and %r", obj1, obj2)

    # Diff the non-primary and non-foreign-key fields.
    user_ro_fields = getattr(obj_class,"__user_ro_fields__",{})
    for k in obj_class.__mapper__.column_attrs.keys():
        if skip_tsv and k.endswith("_tsv"):
            continue

        obj1_val = getattr(obj1,k,None)
        obj2_val = getattr(obj2,k,None)

        # Primary keys and foreign keys are not allowed to change.
        colprop = getattr(obj_class,k).property.columns[0]
        if colprop.primary_key or colprop.foreign_keys:
            if skip_ids:
                continue
            if obj2_val is not None and obj1_val != obj2_val:
                raise ValueError("not allowed to modify primary/foreign key %r" % (k,))
            continue

        # If obj1 and obj2 both came from the DB or from object_from_json, we
        # can assume their types and value constraints are correct.  So we just
        # have to test equivalence.
        if obj2_val != obj1_val:
            if k in user_ro_fields:
                continue
            LOG.debug("diff_by_value: field %r: %r != %r", k, obj1_val, obj2_val)
            opdata = { "obj": obj_class.__name__,
                       "op": "set",
                       "data": { "field": k, "old_value": obj1_val, "value": obj2_val } }
            if path:
                opdata["path"] = path
            curation = model.ArtifactCuration(
                artifact_id=artifact.id,time=curation_time,
                opdata=json.dumps(opdata, cls=CustomJSONEncoder),curator_id=curator_id)
            curations.append(curation)
            if update:
                setattr(obj1,k,obj2_val)

    # Diff relationships.  This is o(n**2), since we don't look at pk/fks, so
    # we must compare every object on every relation list.
    user_ro_relationships = getattr(obj_class,"__user_ro_relationships__",{})
    user_skip_relationships = getattr(obj_class,"__user_skip_relationships__",{})
    for k in obj_class.__mapper__.relationships.keys():
        # We don't care if user does or does not supply these.
        if k in user_skip_relationships or k in user_ro_relationships:
            continue

        relprop = getattr(obj_class,k).property
        if len(relprop.local_columns) > 1:
            raise TypeError("cannot handle relationship with multiple foreign keys")

        (lcc,) = relprop.local_columns

        if False and lcc.foreign_keys:
            # This is a relationship through a foreign key we store in this
            # table, into another table.  We don't allow editing of these keys,
            # so skip it.
            continue

        # We must delete referenced objects if we cannot nullify their foreign
        # keys into this object.
        delete_referenced_objects = False
        for rsk in relprop.remote_side:
            for fk in rsk.foreign_keys:
                # If the foreign key is not nullable, AND
                # If it points into obj_class's table
                if not rsk.nullable and obj_class.__mapper__.local_table.name == fk.column.table.fullname:
                    LOG.debug("diff_by_value: dro: %r %r %r" % (rsk,obj_class.__mapper__.local_table.name,fk.column.table.fullname))
                    delete_referenced_objects = True
                    break

        # Otherwise, this is a relationship into another table via a key in our
        # table, probably our primary key.  We check via recursive value compare
        # if any have been removed, added, or modified.
        deletes = []
        adds = []
        obj1_rval = getattr(obj1,k)
        obj2_rval = getattr(obj2,k)

        # Handle both one-to-one and one-to-many relations in the same code
        # below.
        if not relprop.uselist:
            if obj1_rval:
                obj1_rval = [ obj1_rval ]
            else:
                obj1_rval = []
            if obj2_rval:
                obj2_rval = [ obj2_rval ]
            else:
                obj2_rval = []

        foreign_class = relprop.argument()
        foreign_primary_key = get_primary_key_for_class(foreign_class)
        obj1_rval_pk_map = {}
        obj2_rval_pk_map = {}

        # All we can note is add and del; we cannot detect set without pk/fk
        # awareness.  We *could* try to do more fine-grained patching (e.g.
        # push diffs further down), but not sure there's any point yet.
        i = 0
        for obj1_item in obj1_rval:
            found = False
            for obj2_item in obj2_rval:
                rcurations = artifact_diff_by_value(
                    session, curator, artifact, obj1_item, obj2_item, update=update,
                           path=path + "." + k, skip_ids=skip_ids, skip_tsv=skip_tsv)
                if not rcurations:
                    found = True
                    break
            if not found:
                LOG.debug("diff_by_value: field %r: delete item %r", k, obj1_item)
                deletes.append((i,obj1_item))
            i += 1
        for obj2_item in obj2_rval:
            found = False
            for obj1_item in obj1_rval:
                rcurations = artifact_diff_by_value(
                    session, curator, artifact, obj1_item, obj2_item, update=update,
                           path=path + "." + k, skip_ids=skip_ids, skip_tsv=skip_tsv)
                if not rcurations:
                    found = True
                    break
            if not found:
                LOG.debug("diff_by_value: field %r: add item %r", k, obj2_item)
                adds.append(obj2_item)

        #if rcurations:
        #    curations.extend(rcurations)

        # Make the add/deletes live.
        deletes.reverse()
        if deletes and delete_referenced_objects:
            LOG.debug("diff_by_value: will delete referenced objects of relation %s.%s", obj_class.__name__, k)

        for (i,x) in deletes:
            acj = json.dumps(
                { "obj": foreign_class.__name__,"op": "del",
                "data":{ "field":k,"value": object_to_json(x) } },
                separators=(',',':'))
            ac = model.ArtifactCuration(
                artifact_id=artifact.id,time=curation_time,
                opdata=acj,curator_id=curator_id)
            curations.append(ac)
            if delete_referenced_objects:
                LOG.debug("diff_by_value: deleting referenced object %r", x)
                if update:
                    session.delete(x)
            if not relprop.uselist:
                if update:
                    setattr(obj1,k,None)
            else:
                if update:
                    del getattr(obj1,k)[i]
        for x in adds:
            acj = json.dumps(
                { "obj": foreign_class.__name__,"op": "add",
                  "data":{ "field":k,"value": object_to_json(x) } },
                separators=(',',':'))
            ac = model.ArtifactCuration(
                artifact_id=artifact.id,time=curation_time,
                opdata=acj,curator_id=curator_id)
            curations.append(ac)
            if not relprop.uselist:
                if update:
                    setattr(obj1,k,x)
            else:
                if update:
                    getattr(obj1,k).append(x)
            LOG.debug("added relation %r item: %r" % (k,x))

    return curations

def artifact_apply_curation(session, artifact, curation, update=True, skip_ids=True, skip_tsv=True):
    if not isinstance(artifact,model.Artifact):
        raise TypeError("artifact is not an Artifact")

    LOG.debug("curation: applying curation.id %r to artifact.id %r", curation.id, artifact.id)

    j = {}
    op = None
    (status,msg) = (None,None)

    # Load
    try:
        j = json.loads(curation.opdata)
    except:
        LOG.error("failed to load opdata in %r",curation)
        return (False,"invalid json in opdata")

    # Apply
    try:
        obj_with_field = artifact
        obj_class = None
        if "obj" in j and j["obj"]:
            obj_class = getattr(model,j["obj"])
        op = j["op"]
        field = j.get("data",{}).get("field",None)
        value = j.get("data",{}).get("value",None)
        path = j.get("path","")
        if path and path.startswith("."):
            path = path[1:]
        if path:
            path = path.split(".")
            for subpath in path:
                obj_with_field = getattr(obj_with_field, subpath)

        if op == "set":
            if obj_class and not obj_class.__name__ == obj_with_field.__class__.__name__:
                value = object_from_json(
                    session,obj_class,value,skip_primary_keys=True,skip_tsv=True,
                    error_on_primary_key=False,allow_fk=False,enable_cache=True,
                    should_query=False,never_query=True,obj_cache=None,obj_cache_dicts=None)
                current = getattr(obj_with_field,field)
                res = artifact_diff(
                    session, None, artifact, current, value, update=False, path=path,
                    skip_ids=True, skip_tsv=True)
                if not res:
                    msg = "unchanged"
                elif update:
                    msg = "applied"
                    #session.add(value)
                    setattr(obj_with_field,field,value)
                status = True
            else:
                current = getattr(obj_with_field,field)
                if current == value:
                    msg = "unchanged"
                elif update:
                    msg = "applied"
                    setattr(obj_with_field,field,value)
                status = True
        elif op == "add" or op == "del":
            relprop = getattr(obj_with_field.__class__, field).property
            value = object_from_json(
                session,obj_class,value,skip_primary_keys=True,skip_tsv=True,
                error_on_primary_key=False,allow_fk=False,enable_cache=True,
                should_query=False,never_query=False,obj_cache=None,obj_cache_dicts=None)

            #deletes = []
            if op == "add":
                # check to see if object is already on the list; if not, add
                if relprop.uselist: #isinstance(getattr(obj_with_field,field),list):
                    found = False
                    for x in getattr(obj_with_field,field,[]):
                        res = artifact_diff_by_value(
                            session, None, artifact, x, value, update=False, path=path)
                        if not res:
                            found = True
                            break
                    if found:
                        msg = "unchanged"
                    elif update:
                        msg = "applied"
                        #session.add(value)
                        getattr(obj_with_field,field).append(value)
                    status = True
                else:
                    current = getattr(obj_with_field,field)
                    res = artifact_diff_by_value(
                        session, None, artifact, current, value, update=False, path=path)
                    if not res:
                        msg = "unchanged"
                    elif update:
                        msg = "applied"
                        #session.add(value)
                        setattr(obj_with_field,field,value)
                    status = True
            else:
                # check for the first match and delete it
                # XXX: this means if we are deleting multiple identical objects
                # we will falsely return that the second curation deletes
                # even if there is only one, but that's ok for now.
                if relprop.uselist: #isinstance(getattr(obj_with_field,field),list):
                    found = False
                    (i,x) = (None,None)
                    for i in range(0,len(getattr(obj_with_field,field))):
                        x = getattr(obj_with_field,field)[i]
                        res = artifact_diff_by_value(
                            session, None, artifact, x, value, update=False, path=path)
                        if not res:
                            found = True
                            break
                    if not found:
                        msg = "unchanged"
                    elif update:
                        msg = "deleted"
                        del getattr(obj_with_field,field)[i]
                        # NB: if this object was previously added and is now
                        # being deleted, it will not have been committed to the
                        # DB yet, so we cannot mark it deleted via delete;
                        # instead we must expunge it from the session, lest it
                        # be committed without some required pk/fk.  e.g. in
                        # the case of adding/deleting the same ArtifactBadge
                        # pair, simply calling delete() and removing from the
                        # badges list will result in the insertion of an
                        # ArtifactBadge that simply doesn't have artifact_id
                        # set, and this triggers a null-constraint violation.
                        if sqlalchemy.inspect(x).persistent:
                            session.delete(x)
                        else:
                            session.expunge(x)
                        #deletes.append(x)
                    status = True
                else:
                    current = getattr(obj_with_field,field)
                    res = artifact_diff_by_value(
                        session, None, artifact, current, value, update=False, path=path)
                    found = False
                    if not res:
                        found = True
                    if not found:
                        msg = "unchanged"
                    elif update:
                        msg = "deleted"
                        setattr(obj_with_field,field,None)
                        if sqlalchemy.inspect(current).persistent:
                            session.delete(current)
                        else:
                            session.expunge(current)
                        #deletes.append(current)
                    # Do we ever return False except error?
                    status = True
            #if deletes and update:
            #    #deletes.reverse()
            #    for x in deletes:
            #        LOG.debug("deleting %r",x)
            #        if sqlalchemy.inspect(x).persistent:
            #            session.delete(x)
            #        else:
            #            session.expunge(x)
        else:
            msg = "unsupported curation op %r" % (op,)
            LOG.error(msg)
            return (False, msg)
    except:
        LOG.exception("error applying curation")
        return (False, "error applying curation %d: %r" % (curation.id,sys.exc_info()[1]))

    return (status,msg)

def artifact_apply_curations(session, artifact, curations, update=True, skip_ids=True, skip_tsv=True):
    if not isinstance(artifact,model.Artifact):
        raise TypeError("artifact is not an Artifact")

    results = []

    for curation in curations:
        (status, message) = artifact_apply_curation(session, artifact, curation, update=update, skip_ids=skip_ids, skip_tsv=skip_tsv)
        result.append(dict(curation=curation,status=status,message=message))

    return results

def clone(obj):
    # Create a new artifact_id by cloning the prior, and return it.  Pretty
    # much, anything record with an artifact_id fk has to be cloned to a
    # new pk, and nothing else does.
    #
    # Principle: if we NULL out a PK, if there is a relationship to another
    # table from the table we just nulled, we have to clone that
    # relationship, recursively til it stops.
    #
    #  * this works for Artifact.ArtifactFile.ArtifactFileMember: we NULL
    #    artifact.id, which means we have to go through all Artifact
    #    relationships X and NULL out X.artifact_id and X.id.  Then, if X has
    #    relationships via X.id, we have to recurse on those relationships
    #    and clone them too.  So, concretely, we NULL out ArtifactFile.id and
    #    ArtifactFile.artifact_id, recurse on ArtifactFileMember, and NULL
    #    out its parent_file_id and id, and re-insert all these things into
    #    the relationship list.
    #
    #  * does it work for ArtifactAffiliation.affiliation?  Yes, because
    #    ArtifactAffiliation.id is not the fk into Affiliation.  Said another
    #    way, this is a "forwards" relationship, not a "backwards" one.
    #
    #  * we could run into problems where we have indirect cycles via an
    #    intermediate table, but let's not worry about that for now.
    #
    # Still have to have __clone_skip_relationships__ =
    # ('curations','publication') for the relationships we do not want to
    # pull forward; and __clone_skip_fields__ =
    # ('importer_id','exporter_id','parent_id') ... well, for parent_id we
    # need a custom initializer, ugh, no way around that.

    if not isinstance(obj,db.Model):
        raise TypeError("object not part of the model")

    LOG.debug("clone: cloning %r", obj)

    obj_class = obj.__class__
    pk = get_primary_key_for_class(obj_class)
    clone_skip_fields = getattr(obj_class,"__clone_skip_fields__",())
    clone_skip_relationships = getattr(obj_class,"__clone_skip_relationships__",())

    clone_kwargs = {}
    for k in obj_class.__mapper__.column_attrs.keys():
        if k == pk or k in clone_skip_fields:
            continue
        clone_kwargs[k] = getattr(obj,k,None)

    LOG.debug("clone: fields=%r",clone_kwargs)

    for k in obj_class.__mapper__.relationships.keys():
        if k in clone_skip_relationships:
            continue

        relprop = getattr(obj_class,k).property
        if len(relprop.local_columns) > 1:
            raise TypeError("cannot handle relationship with multiple foreign keys")

        recurse = False
        for rsk in relprop.remote_side:
            for fk in rsk.foreign_keys:
                # If the foreign key points into obj_class's table, clone
                # recursively.
                # XXX should check to see if it points via this class's PK, but
                # that is likely to be true.
                if obj_class.__mapper__.local_table.name == fk.column.table.fullname:
                    recurse = True
                    break

        if recurse:
            # XXX: do we need to explicitly unset the FK field in the foreign obj?
            # or will it simply be overwritten by adding to the parent's relationship?
            cval = None
            if relprop.uselist:
                cval = []
                for rv in getattr(obj,k,[]):
                    cval.append(clone(rv))
            else:
                cval = clone(getattr(obj,k,None))
            clone_kwargs[k] = cval

    cloned_obj = obj_class(**clone_kwargs)

    LOG.debug("clone: returning %r", cloned_obj)

    return cloned_obj

def artifact_clone(artifact):
    if not isinstance(artifact,model.Artifact):
        raise TypeError("artifact is not an Artifact")

    return clone(artifact)

def object_from_json(session,obj_class,j,skip_primary_keys=True,skip_tsv=True,
                     error_on_primary_key=False,allow_fk=False,enable_cache=True,
                     should_query=True,never_query=False,obj_cache=None,obj_cache_dicts=None):
    """
    This function provides hierarchical construction of sqlalchemy objects from JSON.  It handles regular fields and handles recursion ("hierarchy") through relationships.  We use the term hierarchy in the sense that an Artifact may have one or more curations associated with it; so perhaps, less a hierarchy than a tree; but we represent the relationships as children in JSON.  If such "children" have an existing match in the DB, we link those objects directly in (NB: this needs to change to handle permissions or places where we don't want to create a link to existing objects, because the owner needs to ack, or whatever).
    """
    obj_kwargs = dict()

    if enable_cache:
        if obj_cache is None:
            obj_cache = []
        if obj_cache_dicts is None:
            obj_cache_dicts = []

    if j == None:
        LOG.debug("object_from_json: null: %r <- %r" % (obj_class,j))
        return
    else:
        LOG.debug("object_from_json: %r <- %r" % (obj_class,j))

    for k in obj_class.__mapper__.column_attrs.keys():
        colprop = getattr(obj_class,k).property.columns[0]
        # Always skip foreign keys; we want caller to use relations.
        if colprop.foreign_keys and k in j and not allow_fk:
            raise ValueError("foreign keys (%s.%s) always disallowed; use relations" % (
                obj_class.__name__,k))
        # Handle primary_key presence carefully.  If skip_primary_keys==True, we will
        # ignore primary_key presence in json, unless error_on_primary_key==True.  If
        # skip_primary_keys==False, we expect primary keys and error without them,
        # unless error_on_primary_key==False .
        if colprop.primary_key:
            # We are willing to ignore primary keys (e.g. for POST, create new artifact)
            if skip_primary_keys == True:
                # ... but we can also be anal and error on primary_key presence entirely.
                if error_on_primary_key and k in j:
                    raise ValueError("disallowed id key %r" % (k,))
                continue
            # But we might also require them
            if skip_primary_keys == False:
                if k not in j:
                    if error_on_primary_key and not colprop.nullable:
                        raise ValueError("missing required key '%s'" % (k))
                    else:
                        continue
                else:
                    # XXX: need to check to see that the caller has permissions
                    # to reference and/or modify this object... quite tricky.
                    # For instance, caller cannot modify Artifact.owner, nor
                    # can a caller modify an extant person, unless themselves.
                    #
                    # We might need to leave this to to artifact_diff... because we
                    # don't know at this point if we are merely referencing, or if
                    # we are modifying.
                    obj_kwargs[k] = j[k]
                    continue

        if skip_tsv and k.endswith("_tsv"):
            continue

        if k not in j:
            continue

        # Do some basic type checks: python_type equiv, enum validity, length, required.
        if not isinstance(j[k],colprop.type.python_type):
            if colprop.type.python_type in conv_type_map \
              and isinstance(j[k],conv_type_map[colprop.type.python_type]["valid"]):
                try:
                    j[k] = conv_type_map[colprop.type.python_type]["parse"](j[k])
                except:
                    raise ValueError("invalid type for key '%s': should be '%s'" % (
                        k,conv_type_map[colprop.type.python_type]["typeinfo"]))
            elif colprop.nullable and j[k] == None:
                continue
            else:
                raise ValueError("invalid type for key '%s' ('%s'): should be '%s'" % (
                    k,type(j[k]),colprop.type.python_type))
        if hasattr(colprop.type,"length") \
          and colprop.type.length \
          and len(j[k]) > colprop.type.length:
            raise ValueError("value too long for key '%s' (max %d)" % (
                k,colprop.type.length))
        if isinstance(colprop.type,sqlalchemy.sql.sqltypes.Enum) \
          and not j[k] in colprop.type._enums_argument:
            raise ValueError("value for key '%s' not in enumeration set" % (k))

        # Appears valid as far as we can tell.
        obj_kwargs[k] = j[k]

    for k in obj_class.__mapper__.relationships.keys():
        relprop = getattr(obj_class,k).property
        if relprop.backref:
            if k in j:
                raise ValueError("disallowed key '%s'" % (k))
            continue
        # Do some basic checks, and if they pass, attempt to load an
        # existing object from the DB.  If there are multiple objects,
        # raise an error; we don't know what to do.  If there are no
        # objects, recurse and try to obtain one.
        if relprop.uselist:
            if k in j and not isinstance(j[k],list):
                raise ValueError("key '%s' must be a list")
            obj_kwargs[k] = []

        if len(relprop.local_columns) > 1:
            raise TypeError("cannot handle relationship with multiple foreign keys")

        # See if this is a relationship that has a foreign key into another
        # table; or if it's a relationship that uses our primary key into
        # another table.
        (lcc,) = relprop.local_columns
        if lcc.foreign_keys:
            # This is a relationship through a foreign key we store in this
            # table, into another table.  So check to see if that key is
            # nullable.
            colprop = getattr(obj_class,lcc.name).property.columns[0]
            if k in j:
                # Then we need to look for existing objects that match this
                # one, and reference them if they exist.  We look in our cache
                # and in the session.
                if obj_cache and obj_cache_dicts:
                    try:
                        cached = obj_cache_dicts.index(j[k])
                        obj_kwargs[k] = obj_cache[cached]
                        LOG.debug("object_from_json(cache-hit,%r)",j[k])
                        continue
                    except:
                        pass
                foreign_class = relprop.argument()
                next_obj = object_from_json(
                    session,foreign_class,j[k],skip_primary_keys=skip_primary_keys,
                    error_on_primary_key=error_on_primary_key,should_query=True,
                    never_query=never_query,allow_fk=allow_fk,enable_cache=enable_cache,
                    obj_cache=obj_cache,obj_cache_dicts=obj_cache_dicts)
                obj_kwargs[k] = next_obj
                if obj_cache:
                    obj_cache.append(next_obj)
                    obj_cache_dicts.append(j[k])
                continue
        else:
            # This is a relationship into another table via a key in our
            # table, probably our primary key.  These relationships are
            # fundamentally nullable, so nothing to check, just recurse.
            pass
        if not k in j:
            continue
        if relprop.uselist:
            for x in j[k]:
                next_obj = object_from_json(
                    session,relprop.argument(),x,skip_primary_keys=skip_primary_keys,
                    error_on_primary_key=error_on_primary_key,should_query=False,
                    never_query=never_query,allow_fk=allow_fk,enable_cache=enable_cache,
                    obj_cache=obj_cache,obj_cache_dicts=obj_cache_dicts)
                obj_kwargs[k].append(next_obj)
        else:
            next_obj = object_from_json(
                session,relprop.argument(),j[k],skip_primary_keys=skip_primary_keys,
                error_on_primary_key=error_on_primary_key,should_query=False,
                never_query=never_query,allow_fk=allow_fk,enable_cache=enable_cache,
                obj_cache=obj_cache,obj_cache_dicts=obj_cache_dicts)
            obj_kwargs[k] = next_obj

    # Query the DB iff all top-level obj_kwargs are basic types or persistent
    # objects, and if our parent told us we should query.
    if not never_query and should_query:
        can_query = True
        for kwa in list(obj_kwargs):
            if isinstance(obj_kwargs[kwa],list):
                # This is a relation list, so we can't query for this object
                # like this.
                can_query = False
            if not isinstance(obj_kwargs[kwa],db.Model):
                continue
            try:
                state = sqlalchemy.inspect(obj_kwargs[kwa])
                can_query = getattr(state, "persistent", False)
            except:
                pass
            if not can_query:
                break
        if can_query:
            q = session.query(obj_class)
            for kwa in list(obj_kwargs):
                q = q.filter(getattr(obj_class,kwa).__eq__(obj_kwargs[kwa]))
            qres = q.all()
            if qres:
                if obj_cache:
                    obj_cache.append(qres[0])
                    obj_cache_dicts.append(j)
                if qres[0] in session:
                    LOG.debug("object_from_json(in=True,query): %r",qres[0])
                else:
                    LOG.debug("object_from_json(in=False,query): %r",qres[0].__class__.__name__)
                return qres[0]

    ret = obj_class(**obj_kwargs)
    if ret in session:
        LOG.debug("object_from_json(in=True): %r",ret)
    else:
        LOG.debug("object_from_json(in=False): %r",ret.__class__.__name__)
    return ret


jsontypes = (dict,list,tuple,str,int,float,bool,type(None))

def object_to_json(o,recurse=True,skip_ids=True,skip_tsv=True):
    if not isinstance(o,db.Model):
        raise ValueError("object %r not an instance of our model.Base" % (o))

    j = {}

    for k in o.__class__.__mapper__.column_attrs.keys():
        colprop = getattr(o.__class__,k).property.columns[0]
        if skip_ids and (colprop.primary_key or colprop.foreign_keys):
            continue
        if skip_tsv and k.endswith("_tsv"):
            continue
        v = getattr(o,k,"")
        if v is None:
            continue
        elif isinstance(v,bytes):
            v = base64.b64encode(v).decode('utf-8')
        elif not isinstance(v,jsontypes):
            v = str(v)
        j[k] = v
    if not recurse:
        return j

    for k in o.__class__.__mapper__.relationships.keys():
        relprop = getattr(o.__class__,k).property
        if k.startswith("parent_") or relprop.backref or relprop.viewonly:
            continue
        #print("%r.%r" %(o.__class__,k))
        v = getattr(o,k,None)
        if v is None:
            continue
        if isinstance(v,list):
            nl = []
            for x in v:
                if isinstance(x,db.Model):
                    nl.append(object_to_json(x,recurse=recurse,skip_ids=skip_ids))
                else:
                    nl.append(x)
            v = nl
        elif isinstance(v,db.Model):
            v = object_to_json(v,recurse=recurse,skip_ids=skip_ids)
        elif isinstance(v,bytes):
            v = v.decode('utf-8')
        elif not isinstance(v,jsontypes):
            v = str(v)
        j[k] = v
    return j

python_jsonschema_type_map = {
    str: "string",
    bytes: "string",
    float: "float",
    int: "int",
    datetime.datetime: "string"
}
def conv_python_type_to_jsonschema(t):
    if t in python_jsonschema_type_map:
        return python_jsonschema_type_map[t]
    return "string"

def class_to_jsonschema(kls,skip_pk=True,skip_fk=True,skip_relations=False,
                        defs=None,root=True):
    #if not isinstance(o,db.Model):
    #    raise ValueError("object %r not an instance of our model.Base" % (o))
    if not defs:
        defs = {}
    name = kls.__name__
    if name in defs:
        return

    typedef = {
        "description": name, "type": "object", "required": [], "properties": {}
    }
    defs[name] = typedef

    user_ro_fields = getattr(kls,"__user_ro_fields__",{})
    for k in kls.__mapper__.column_attrs.keys():
        colprop = getattr(kls,k).property.columns[0]
        if skip_pk and colprop.primary_key:
            continue
        if skip_fk and colprop.foreign_keys:
            continue
        if k in user_ro_fields:
            continue
        if isinstance(colprop.type,sqlalchemy.sql.sqltypes.Enum):
            typedef["properties"][k] = dict(type="string",enum=colprop.type._enums_argument)
            if not colprop.nullable:
                typedef["required"].append(k)
        else:
            pt = None
            try:
                pt = str(colprop.type.python_type.__name__)
            except:
                continue
            typedef["properties"][k] = dict(type=conv_python_type_to_jsonschema(pt))
            if pt == "bytes":
                typedef["properties"][k]["format"] = "byte"

            if not colprop.nullable:
                typedef["required"].append(k)

    #
    # NB: the commented bits are to support the LCD of jsonschema generators.
    #
    if not skip_relations:
        user_ro_relationships = getattr(kls,"__user_ro_relationships__",{})
        user_skip_relationships = getattr(kls,"__user_skip_relationships__",{})
        for k in kls.__mapper__.relationships.keys():
            relprop = getattr(kls,k).property
            if k.startswith("parent_") or relprop.backref or relprop.viewonly:
                continue
            if k in user_ro_relationships or k in user_skip_relationships:
                continue
            fclass = relprop.argument()
            fname = fclass.__name__
            if relprop.uselist:
                typedef["properties"][k] = {
                    "type": "array",
                    "items": {
                        #"schema": {
                            "$ref": "#/definitions/%s" % (fname,)
                        #}
                    }
                }
            else:
                typedef["properties"][k] = {
                    #"type": "object",
                    #"schema": {
                        "$ref": "#/definitions/%s" % (fname,)
                    #}
                }
            class_to_jsonschema(
                fclass,skip_pk=skip_pk,skip_fk=skip_fk,skip_relations=skip_relations,
                defs=defs,root=False)

    if root:
        ret = {
            "id": "https://hub.cyberexperimentation.org/v1/schema/%s.schema.json" % (name,),
            #"$schema": "https://json-schema.org/draft/2020-12/schema",
            #"description": name,
            #"type": "object",
            #"$ref": "#/definitions/%s" % (name,),
            "definitions": defs
        }
        ret.update(typedef)
        return ret
    else:
        return
