var channelboard = (function() {
    function Channel(frequency, is_control, department, description) {
	this.frequency = frequency;
	this.is_control = is_control;
	this.department = department;
	this.description = description;

	this.xmitting = false;

	this.getFrequency = function() { return this.frequency; }
	this.isControl = function() { return this.is_control; }
	this.getDepartment = function() { return this.department; }
	this.getDescription = function() { return this.description; }

	this.startXmit = function() { this.xmitting = true; }
	this.stopXmit = function() { this.xmitting = false; }

	this.isXmit = function() { return this.xmitting; }

	this.div = undefined;

	this.updateHTML = function() {
	    this.div.innerHTML = this.getFrequency() + " / " + this.getDescription();
	};
    };

    function channelFrom(d) {
	return new Channel(d["frequency"], d["is_control"], d["department"], d["description"]);
    };

    function ChannelBoard(div, channels) {
	this.div = div;
	this.channels = channels;

	this.channel_divs = []; 

	// create a coindexed list of html elements for the channels

	html = "";

	for (var i = 0; i < channels.length; i++) {
	    var c = channels[i];

	    var chan_class = "channel_status";
	    if (c.isControl()) chan_class = "channel_status_control";

	    var curdiv = document.createElement("div");

	    c.div = curdiv;

	    curdiv.classList.add(chan_class);
	    if (!c.isControl()) curdiv.classList.add("channel_xmit_unknown");
	    curdiv.id = "channel_status_" + c.getFrequency();

	    c.updateHTML();
	    this.channel_divs.push(curdiv);

	    this.div.append(curdiv);
	}


	this.channelIndex = function(freq) {
	    for (var i = 0; i < this.channels.length; i++) {
		if (this.channels[i].frequency == freq) {
		    return i;
		}
	    }
	    return -1;
	};

	this.channelStart = function(freq) {
	    var i = this.channelIndex(freq);
	    if (-1 == i) return;

	    if (this.channels[i].isControl()) return;

	    this.channel_divs[i].classList.remove("channel_xmit_unknown");
	    this.channel_divs[i].classList.remove("channel_xmit_noxmit");
	    this.channel_divs[i].classList.add("channel_xmit_inxmit");

	    if (this.channels[i].getDescription() == "-idle-") {
		this.channels[i].description = "????";
		this.channels[i].updateHTML();
	    }
	};


	this.channelStop = function(freq) {
	    var i = this.channelIndex(freq);
	    if (-1 == i) return;
	    if (this.channels[i].isControl()) return;

	    this.channel_divs[i].classList.remove("channel_xmit_unknown");
	    this.channel_divs[i].classList.remove("channel_xmit_inxmit");
	    this.channel_divs[i].classList.add("channel_xmit_noxmit");

	    this.channels[i].description = "-idle-";
	    this.channels[i].updateHTML();
	};

	this.channelTag = function(freq, tg) {
	    var i = this.channelIndex(freq);
	    if (-1 == i) return;
	    if (this.channels[i].isControl()) return;

	    this.channels[i].description = tg;
	    this.channels[i].updateHTML();
	};

    };


    var channel_list = [
	{ "frequency": 851125000, "is_control": true, "department": "Safety", "description": "" },
	{ "frequency": 851150000, "is_control": true, "department": "Safety", "description": "" },
	{ "frequency": 851400000, "is_control": true, "department": "Safety", "description": "" },
	{ "frequency": 851425000, "is_control": true, "department": "Safety", "description": "" },
	{ "frequency": 851587500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 851612500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 851762500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 851812500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 852087500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 852212500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 852262500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 852387500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 852675000, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 852837500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 853087500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 853225000, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 853412500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 853437500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 853625000, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 853650000, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 853787500, "is_control": false, "department": "Safety", "description": "" },
	{ "frequency": 853887500, "is_control": false, "department": "Safety", "description": "" },
    ];


    var all_channels = $.map(channel_list, channelFrom);


    var cb = new ChannelBoard($("#channelboard"), all_channels);
    return cb;
})();
