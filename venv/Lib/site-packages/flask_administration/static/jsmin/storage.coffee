define ['library/underscore', 'library/backbone', 'library/underscore.string'], (_, Backbone, string) ->
  _.mixin string.exports()
  S4: ->
    (((1+Math.random())*0x10000)|0).toString(16).substring(1)
  guid: ->
    (S4()+S4()+"-"+S4()+"-"+S4()+"-"+S4()+"-"+S4()+S4()+S4())

  class Store
    constructor: (@name) ->
      @store = localStorage.getItem @name
      @data = (@store and JSON.parse(@store)) or {}
