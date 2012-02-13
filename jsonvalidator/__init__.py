'''
* JSON schema data validation.
* Author: Maxim Derkachev (max.derkachev@gmail.com)
* http://www.ragbag.ru/2007/05/03/json_validator/lang/en/
* 
Schema is a JSON-compatible string or Python object, is an example of a valid data structure.
Example schemas:
*   '["string", "number"]'
    '["anything", 1]'
    Valid for [], [3], [""], ["something", 4, "foo"]
    Invalid for {}, 1, "", [true], [1, false]

*   {"one": 1, "two": {"three":"string?"}}
    Valid for {"one":0, "two":{}}, {"one":0, "two":{"three":"something"}}, {"one":2, "two":{"three":""}}
    Invalid for 1, "", [], {}, {"one":0}, {"one":0, "two":{"three":1}}, {"one":0, "two":{}, "foo":"bar"}

The following schemas are equivalent:
1. {"a":"there can be a string"}, {"a": "string"}, {"a": ""}
2. {"b":4563}, {"b": 0}, {"b": "number"}

Value types can be defined as:
*  literals of that type, e.g. {} for object, [] for array, 
   1 for number, "anything" for string, null for null, false or true for boolean; 
* "string" for string, "number" for number, "bool" for boolean. In this case you can add "?"
  to indicate that the value can be undefined or null. E.g. "number?" is matched by numbers,
  undefined values and nulls


* API:
# JSON string
schema = '["string", "number"]'
# or an object:
schema = ["any string", 1]
validator = JSONValidator(schema)
isValid = validator.validate(data) # data is a Python object  or a JSON string

Raise JSONError on invalid JSON (that can not be parsed),
or JSONValidationError (no JSON parse errors, but invalid for the schema specified)
'''

'''
Software License Agreement (BSD License)

Copyright (c) 2007, Maxim Derkachev.
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
  * Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.
  * Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.
  * Neither the name of the Maxim Derkachev nor the names of its contributors
    may be used to endorse or promote products derived from this software
    without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


try:
  import json
except ImportError:
  import simplejson as json

import types
import re

class PermissiveObject(dict):
  """Wrap your dictionary in this (or build a dictionary from this by using
  the normal dictionary keyword constructor) and the validator will use the
  permissive dictionary validation instead of the default strict validation.
  """

class JSONValidationError(Exception):
  pass

class JSONError(Exception):
  pass


class BaseHandler(object):
  def __init__(self, schema, required):
    self.required = required
    
  def __call__(self, data, key=None):
    return self.validate(data, key)

  def validate(self, data, key=None):
    if data is None and self.required:
      if key:
        message = "Required field with key \"%s\" is missing" % key
      else:
        message = "Required field is missing"
      raise JSONValidationError(message)
    return data
                    

class StringHandler(BaseHandler):
  def validate(self, data, key=None):
    data = super(StringHandler, self).validate(data, key)
    if data and not isinstance(data, basestring):
      message = _keyMessage(key, "is not a string: %s" % data)
      raise JSONValidationError(message)
    return data
  
class ReHandler(BaseHandler):
  def __init__(self, schema, required):
    super(ReHandler, self).__init__(schema, required)
    self.pattern = schema

  def validate(self, data, key=None):
    data  = super(ReHandler, self).validate(data, key)
    try:
      match = self.pattern.match(data)
    except TypeError:
      raise JSONValidationError(
          _keyMessage(key, "cannot be used in a regex: %s" % data))
    if not match:
      raise JSONValidationError(
        _keyMessage(key, "does not fit re: %s" % data))
    return data
  
  @classmethod
  def getType(self):
    return type(re.compile(''))

class NumberHandler(BaseHandler):
  def validate(self, data, key=None):
    data = super(NumberHandler, self).validate(data, key)
    if data and not isinstance(data, (int, long, float)):
      message = _keyMessage(key, "is not a number: %s" % data)
      raise JSONValidationError(message)
    return data

class BooleanHandler(BaseHandler):
  def validate(self, data, key=None):
    data = super(BooleanHandler, self).validate(data, key)
    if data is not None and not isinstance(data, bool):
      message = _keyMessage(key, "is not a boolean: %s" % data)
      raise JSONValidationError(message)
    return data

class NullHandler(BaseHandler):
  def validate(self, data, key=None):
    if not isinstance(data, types.NoneType):
      message = _keyMessage(key, "is not null: %s" % data)
      raise JSONValidationError(message)
    return data


class ObjectHandler(BaseHandler):
  def __init__(self, schema, required):
    super(ObjectHandler, self).__init__(schema, required)
    self.handlers = {}
    self.validKeys = set()
    for key, value in schema.items():
      _type, handler = getValidator(value)
      self.handlers[key] = handler
      self.validKeys.add(key)
    
  def validate(self, data, mykey=None):
    data = super(ObjectHandler, self).validate(data, mykey)
    if not isinstance(data, dict):
      message = _keyMessage(mykey, "is not an object: %s" % data)
      raise JSONValidationError(message)

    handlers = self.handlers
    for key, handler in handlers.items():
      keyData = data.get(key, None)
      keydata = handler(keyData, '%s/%s' % (mykey, key))

    if self.validKeys:
      for key in data:
        if not key in self.validKeys:
          message = _keyMessage(mykey, "contains an illegal key: %s" % key)
          raise JSONValidationError(message)
    return data

class PermissiveObjectHandler(ObjectHandler):
  """Just like a normal object handler except that it ignores unknown keys in
  the validating dictionary.
  """
  def __init__(self, schema, required):
    super(PermissiveObjectHandler, self).__init__(schema, required)
    self.validKeys = None


class ArrayHandler(BaseHandler):
  def __init__(self, schema, required):
    super(ArrayHandler, self).__init__(schema, required)
    self.handlers = {}
    for value in schema:
      tpe, handler = getValidator(value)
      self.handlers[tpe] = handler

  def validate(self, data, key=None):
    data = super(ArrayHandler, self).validate(data, key)
    if not isinstance(data, list):
      message = _keyMessage(key, "is not an array: %s" % data)
      raise JSONValidationError(message)
    elif not self.handlers:
      return data
    elif not self.handlers.get(types.NoneType, False) and not data:
      message = _keyMessage(key, "should not be empty: %s" % data)
      raise JSONValidationError(message)

    for idx, value in enumerate(data):
      handler = self.handlers.get(type(value), None)
      if not handler:
        message = "Element at index %d has invalid type %s" % (idx, value)
        raise JSONValidationError(message)
      value = handler(value, '%s/%s' % (key, idx))
    return data    


HANDLERS_BY_TYPE = {
    str                 : StringHandler,
    unicode             : StringHandler,
    int                 : NumberHandler,
    long                : NumberHandler,
    float               : NumberHandler,
    dict                : ObjectHandler,
    list                : ArrayHandler,
    bool                : BooleanHandler,
    type(None)          : NullHandler,
    ReHandler.getType() : ReHandler,
    PermissiveObject    : PermissiveObjectHandler,
    }

def getValidator(schema):
  required = True
  tpe = type(schema)
  if tpe in types.StringTypes:
    if schema.startswith("number"):
      tpe = int
    elif schema.startswith("bool"):
      tpe = bool
    required = not schema.endswith('?')
  handler = HANDLERS_BY_TYPE.get(tpe, None)
  if handler:
    return tpe, handler(schema, required)
  else:
    raise JSONError("Unsupported JSON type in schema")

class JSONValidator(object):
  validator = None

  def __init__(self, schema):
    if isinstance(schema, basestring):
      schema = json.loads(schema)
    _type, self.validator = getValidator(schema)

  def validate(self, data):
    if self.validator:
      if isinstance(data, basestring):
        parsedData = json.loads(data)
        if not parsedData:
          raise JSONError("invalid JSON in %s" % data)
        data = parsedData
      return self.validator(data)

def _keyMessage(key, rest):
  if key:
    return "Data at %s %s" % (key, rest)
  return "Data %s" % rest

