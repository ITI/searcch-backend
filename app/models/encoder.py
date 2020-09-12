from sqlalchemy.ext.declarative import DeclarativeMeta
import json
from bson import json_util
from datetime import datetime

def alchemy_encoder():
    _visited_objs = []

    class AlchemyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj.__class__, DeclarativeMeta):
                # don't re-visit self
                if obj in _visited_objs:
                    return None
                _visited_objs.append(obj)

                # an SQLAlchemy class
                fields = {}
                print(dir(obj))
                for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                    if isinstance(obj.__getattribute__(field), datetime):
                        print('{} from {} is of datetime type'.format(field, obj.__repr__))
                        fields[field] = obj.__getattribute__(field).isoformat()
                    else:
                        fields[field] = obj.__getattribute__(field)
                # a json-encodable dict
                return fields
            
            return json.JSONEncoder.default(self, obj)

    return AlchemyEncoder


def to_json(inst, cls):
    """
    Jsonify the sqlalchemy query result.
    """
    convert = dict()
    # add your coversions for things like datetime's 
    # and what-not that aren't serializable.
    d = dict()
    for c in cls.__table__.columns:
        v = getattr(inst, c.name)
        if c.type in convert.keys() and v is not None:
            try:
                d[c.name] = convert[c.type](v)
            except:
                d[c.name] = "Error:  Failed to covert using ", str(convert[c.type])
        elif v is None:
            d[c.name] = str()
        else:
            d[c.name] = v
    return json.dumps(d)