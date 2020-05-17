(function() {
  var Store;

  ({
    S4: function() {
      return (((1 + Math.random()) * 0x10000) | 0).toString(16).substring(1);
    },
    guid: function() {
      return S4() + S4() + "-" + S4() + "-" + S4() + "-" + S4() + "-" + S4() + S4() + S4();
    }
  });

  Store = (function() {

    function Store(name) {
      this.name = name;
      this.store = localStorage.getItem(this.name);
      this.data = (this.store && JSON.parse(this.store)) || {};
    }

    Store.prototype.save = function() {
      return localStorage.setItem(this.name, JSON.stringify(this.data));
    };

    Store.prototype.create = function(model) {
      if (!model.id) model.id = model.attributes.id = guid();
      this.data[model.id] = model;
      this.save();
      return model;
    };

    return Store;

  })();

}).call(this);
