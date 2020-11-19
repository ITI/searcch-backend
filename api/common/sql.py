
import sqlalchemy
import datetime

from api.app import db
from models import model

def object_from_json(session,obj_class,j,skip_ids=True,should_query=True,
                     obj_cache=[],obj_cache_dicts=[]):
    obj_kwargs = dict()

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

    for k in obj_class.__mapper__.column_attrs.keys():
        # Skip primary keys or foreign keys.
        colprop = getattr(obj_class,k).property.columns[0]
        if skip_ids and (colprop.primary_key or colprop.foreign_keys):
            if k in j:
                raise ValueError("disallowed id key '%s'" % (k,))
            continue
        # Do some basic type checks: python_type equiv, enum validity, length, required.
        if not colprop.nullable and not k in j:
            raise ValueError("missing required key '%s'" % (k))
        elif not k in j:
            continue
        if not isinstance(j[k],colprop.type.python_type):
            if colprop.type.python_type in conv_type_map \
              and isinstance(j[k],conv_type_map[colprop.type.python_type]["valid"]):
                try:
                    j[k] = conv_type_map[colprop.type.python_type]["parse"](j[k])
                except:
                    raise ValueError("invalid type for key '%s': should be '%s'" % (
                        k,conv_type_map[colprop.type.python_type]["typeinfo"]))
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
            if not isinstance(j[k],list):
                raise ValueError("key '%s' must be a list")
            obj_kwargs[k] = []

        # See if this is a relationship that has a foreign key into another
        # table; or if it's a relationship that uses our primary key into
        # another table.
        lcc = relprop.local_columns.copy().pop()
        if lcc.foreign_keys:
            # This is a relationship through a foreign key we store in this
            # table, into another table.  So check to see if that key is
            # nullable.
            colprop = getattr(obj_class,lcc.name).property.columns[0]
            if not colprop.nullable and not k in j:
                raise ValueError("missing required key '%s' (%r)" % (k,j))
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
                    session,foreign_class,j[k],skip_ids=skip_ids,should_query=True,
                    obj_cache=obj_cache,obj_cache_dicts=obj_cache_dicts)
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
                    session,relprop.argument(),x,skip_ids=skip_ids,should_query=False,
                    obj_cache=obj_cache,obj_cache_dicts=obj_cache_dicts)
                obj_kwargs[k].append(next_obj)
        else:
            next_obj = object_from_json(
                session,relprop.argument(),j[k],skip_ids=skip_ids,
                obj_cache=obj_cache,obj_cache_dicts=obj_cache_dicts)
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
