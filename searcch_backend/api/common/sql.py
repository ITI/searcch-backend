
import sqlalchemy
import datetime
import logging
import json

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
        "parse": lambda x: bytes(x,"utf-8"),
        "valid": str,
        "typeinfo": str
    }
}

def get_primary_key_for_class(model_class):
    for k in model_class.__mapper__.column_attrs.keys():
        # Skip primary keys or foreign keys.
        colprop = getattr(model_class,k).property.columns[0]
        if colprop.primary_key:
            return k
    return None

def artifact_diff(session,artifact, obj1, obj2, update=True, path=""):
    if not isinstance(artifact,model.Artifact):
        raise TypeError("artifact is not an Artifact")
    if type(obj1) != type(obj2):
        raise TypeError("object type mismatch (%r,%r)" % (type(obj1),type(obj2)))
    if not isinstance(obj1,db.Model):
        raise TypeError("object not part of the model")

    curations = []
    obj_class = obj1.__class__

    #
    # Be warned -- if `obj2` has any unset nullable=False fields, and if a
    # `session.refresh` is triggered, sqlalchemy will fail to load the object.
    # This is a useful canary-in-the-coal-mine for now.
    #
    LOG.debug("updating %r and %r" % (repr(obj1),repr(obj2)))

    # Diff the non-primary and non-foreign-key fields.
    user_ro_fields = getattr(obj_class,"__user_ro_fields__",{})
    for k in obj_class.__mapper__.column_attrs.keys():
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
            curation = model.ArtifactCuration(
                artifact_id=artifact.id,time=datetime.datetime.now(),
                opdata=json.dumps(
                    { "path": path,
                      "obj": obj_class.__name__,
                      "op": "set",
                      "data": { "field": k, "value": obj2_val } }),
                curator_id=artifact.owner_id)
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
            val = getattr(x,foreign_primary_key,None)
            if val is not None:
                if val not in obj1_rval_pk_map:
                    if not getattr(foreign_class,"__object_from_json_allow_pk__",False):
                        raise ValueError("cannot set primary key to value not present in original object")
                    LOG.debug("added relation %r item: %r" % (k,x))
                    adds.append(x)
                obj2_rval_pk_map[val] = (i,x)
            else:
                LOG.debug("added relation %r item: %r" % (k,x))
                adds.append(x)
        # Look for deletions.
        for (o1k,o1v) in obj1_rval_pk_map.items():
            if not o1k in obj2_rval_pk_map:
                LOG.debug("deleted relation %r item: %r" % (o1k,o1v,))
                deletes.append(o1v)
        # Trawl for possible modifications.
        for (o1k,(o1i,o1v)) in obj1_rval_pk_map.items():
            if not o1k in obj2_rval_pk_map:
                # NB: this just happens because we don't modify the maps as we
                # journal additions/deletions; so ignore.
                continue
            # Finally, recurse:
            (o2i,o2v) = obj2_rval_pk_map[o1k]
            rcurations = artifact_diff(session,artifact,o1v,o2v,update=update,path=path+"."+k)
            if rcurations:
                curations.extend(rcurations)

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
                opdata=acj,curator_id=artifact.owner_id)
            curations.append(ac)
            if delete_referenced_objects:
                LOG.debug("deleting referenced object %r",x)
                session.delete(x)
            del getattr(obj1,k)[i]
        for x in adds:
            acj = json.dumps(
                { "obj": foreign_class.__name__,"op": "add",
                "data":{ "field":k,"value": object_to_json(x) } },
                separators=(',',':'))
            ac = model.ArtifactCuration(
                artifact_id=artifact.id,time=datetime.datetime.now(),
                opdata=acj,curator_id=artifact.owner_id)
            curations.append(ac)
            getattr(obj1,k).append(x)

    return curations

def object_from_json(session,obj_class,j,skip_primary_keys=True,error_on_primary_key=False,
                     allow_fk=False,
                     should_query=True,obj_cache=[],obj_cache_dicts=[]):
    """
    This function provides hierarchical construction of sqlalchemy objects from JSON.  It handles regular fields and handles recursion ("hierarchy") through relationships.  We use the term hierarchy in the sense that an Artifact may have one or more curations associated with it; so perhaps, less a hierarchy than a tree; but we represent the relationships as children in JSON.  If such "children" have an existing match in the DB, we link those objects directly in (NB: this needs to change to handle permissions or places where we don't want to create a link to existing objects, because the owner needs to ack, or whatever).
    """
    obj_kwargs = dict()

    LOG.debug("object_from_json: %r -> %r" % (obj_class,j))

    if j == None:
        LOG.debug("null json value: %r %r" % (obj_class,j))
        return

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
                        continue
                    except:
                        pass
                foreign_class = relprop.argument()
                next_obj = object_from_json(
                    session,foreign_class,j[k],skip_primary_keys=skip_primary_keys,
                    error_on_primary_key=error_on_primary_key,should_query=True,
                    allow_fk=allow_fk,obj_cache=obj_cache,obj_cache_dicts=obj_cache_dicts)
                obj_kwargs[k] = next_obj
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
                    allow_fk=allow_fk,obj_cache=obj_cache,obj_cache_dicts=obj_cache_dicts)
                obj_kwargs[k].append(next_obj)
        else:
            next_obj = object_from_json(
                session,relprop.argument(),j[k],skip_primary_keys=skip_primary_keys,
                error_on_primary_key=error_on_primary_key,should_query=False,
                allow_fk=allow_fk,obj_cache=obj_cache,obj_cache_dicts=obj_cache_dicts)
            obj_kwargs[k] = next_obj

    # Query the DB iff all top-level obj_kwargs are basic types or persistent
    # objects, and if our parent told us we should query.
    if should_query:
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
                obj_cache.append(qres[0])
                obj_cache_dicts.append(j)
                return qres[0]

    return obj_class(**obj_kwargs)

jsontypes = (dict,list,tuple,str,int,float,bool,type(None))

def object_to_json(o,recurse=True,skip_ids=True):
    if not isinstance(o,db.Model):
        raise ValueError("object %r not an instance of our model.Base" % (o))

    j = {}

    for k in o.__class__.__mapper__.column_attrs.keys():
        colprop = getattr(o.__class__,k).property.columns[0]
        if skip_ids and (colprop.primary_key or colprop.foreign_keys):
            continue
        v = getattr(o,k,"")
        if v is None:
            continue
        elif isinstance(v,bytes):
            v = v.decode('utf-8')
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
    str: "string",bytes: "string",float: "float",int: "int",datetime.datetime: "string"
}
def conv_python_type_to_jsonschema(t):
    if t in python_jsonschema_type_map:
        return python_jsonschema_type_map[t]
    return "string"

def class_to_jsonschema(kls,skip_pk=True,skip_fk=True,skip_relations=False,
                        defs={},root=True):
    #if not isinstance(o,db.Model):
    #    raise ValueError("object %r not an instance of our model.Base" % (o))
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
