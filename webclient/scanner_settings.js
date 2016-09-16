function ScannerSettings() {
    var min_v = 1; // minimum version we can use

    var values = { "v": 1 }; // key=>value store

    this.getValues = function() { return values; };

    this.loadFromCookie = function() {
	var newvalues = {};

	try {
	    newvalues = JSON.parse(document.cookie)

	    if (newvalues.v < min_v) {
		console.error("Obsolete cookie: min_v=" + min_v + ", but v=" + newvalues.v);
		return;
	    }

	    values = newvalues;
	} catch(e) {
	    console.error("Error parsing cookie: " + document.cookie)
	    document.cookie = null;
	    // do nothing
	}
    };


    var saveToCookie = function() {
	document.cookie = JSON.stringify(values);
    };
    this.saveToCookie = saveToCookie;

    this.set = function(k, v) {
	values[k] = v;
	saveToCookie();
    };

    this.get = function(k) {
	return values[k];
    };

    return this;
};
