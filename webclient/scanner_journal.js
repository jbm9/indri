var scanner_journal = (function() {
    function ScannerJournal() {
	var time_offset = 0; // Time delta between browser time and server time, milliseconds
	var journal = [];    // List of entries, of the form { ts: N, tg: N, freq: f, path: url, len: length in seconds }

	var group_calls = []; // List of call opens, { ts: N, tg: N, freq: f }
	var file_completes = []; // List of file uploads, { ts: N, tg: N, freq: f, path, URL }

	var cutoff = 10*10*1000; // how long to keep items, milliseconds

	this.setTimeOffset = function(dt) {
	    time_offset = dt;
	};


	this.cull = function() {
	    var d = new Date();
	    var tnow = d.getTime() - time_offset; // time, on server

	    journal = journal.filter(function(e,i,a) { return e.ts + cutoff > tnow; })
	};

	this.push = function(evt) {
	    journal.push(evt);
	};

    };
    

    var sj = new ScannerJournal();

    return sj;
})();
