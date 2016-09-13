function ScannerConfig() {
    var config = {};
    var callbacks = []; // list of things to call back when config updates
    var got_config = false;

    this.updateConfig = function(response) {
	console.log("Got a config update");
	config = response.config;

	for (var i = 0; i < callbacks.length; i++) {
	    var cb = callbacks[i];
	    cb(config);
	}

	got_config = true;
    }

    this.register = function(cb) {
	callbacks.push(cb);
	if (got_config) cb(config);
    }

    return this;
}
