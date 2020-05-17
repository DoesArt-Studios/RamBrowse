
S4: ->
  (((1+Math.random())*0x10000)|0).toString(16).substring(1)

guid: ->
  (S4()+S4()+"-"+S4()+"-"+S4()+"-"+S4()+"-"+S4()+S4()+S4())

class Store
  constructor: (@name) ->
    @store = localStorage.getItem @name
    @data = (@store and JSON.parse(@store)) or {}

  save: ->
    localStorage.setItem @name, JSON.stringify @data

  create: (model) ->
    if not model.id
      model.id = model.attributes.id = guid()
    @data[model.id] = model
    @save()
    model