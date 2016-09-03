var channelboard = (function() {
    var tgs = [{"category": "Interop", "tg": 13680, "short": "MA", "long": "Mobile Assistance Patrol"}, {"category": "Law Talk", "tg": 15504, "short": "CORONE", "long": "Coroner Administration"}, {"category": "Law Tac", "tg": 16464, "short": "DPT A", "long": "PCO Dispatch"}, {"category": "Law Tac", "tg": 16496, "short": "DPT A", "long": "PTC Administration & Engineering"}, {"category": "Public Works", "tg": 16528, "short": "DPT A", "long": "Traffic Signal Shop"}, {"category": "Public Works", "tg": 16560, "short": "DPT A", "long": "Parking Meter-Signs-Paint Shops"}, {"category": "Law Tac", "tg": 16592, "short": "DPT A", "long": "PTC Special Events"}, {"category": "Public Works", "tg": 16624, "short": "DPT A", "long": "Traffic Control Center"}, {"category": "Law Tac", "tg": 16656, "short": "SCOF", "long": "Parking Scofflaws (also SFPD A-15 \"\"SCOFFLAW\"\")"}, {"category": "Law Tac", "tg": 16688, "short": "TO", "long": "Parking Towaway (also SFPD A-16 \"\"TOW CH\"\")"}, {"category": "Utilities", "tg": 16816, "short": "WATER ", "long": "Water Department 1 Administration"}, {"category": "Utilities", "tg": 16848, "short": "WATER ", "long": "Water Department 2 Operations"}, {"category": "Public Works", "tg": 16912, "short": "REC A", "long": "Recreation & Parks A-1 Admin-Rec-Marina-Events"}, {"category": "Public Works", "tg": 16944, "short": "REC A", "long": "Recreation & Parks A-2 Structural Maintenance"}, {"category": "Public Works", "tg": 16976, "short": "REC A", "long": "Recreation & Parks A-3 Park Maint Urban Forestry"}, {"category": "Security", "tg": 17008, "short": "REC A", "long": "Recreation & Parks A-4 Park Patrol"}, {"category": "Public Works", "tg": 17040, "short": "REC A", "long": "Recreation & Parks A-5 3-Com Park"}, {"category": "Other", "tg": 17648, "short": "RADIO A", "long": ""}, {"category": "Other", "tg": 17680, "short": "RADIO A", "long": ""}, {"category": "Other", "tg": 17712, "short": "RADIO A", "long": ""}, {"category": "Other", "tg": 17744, "short": "RADIO A", "long": ""}, {"category": "Other", "tg": 17776, "short": "RADEM", "long": ""}, {"category": "Other", "tg": 18160, "short": "CCSFPO", "long": ""}, {"category": "Other", "tg": 18544, "short": "MYTAL", "long": ""}, {"category": "Security", "tg": 50000, "short": "", "long": "Public Library Security - Main and Branches"}, {"category": "Public Works", "tg": 64976, "short": "UN", "long": "Street Sweepers"}, {"category": "Interop", "tg": 13520, "short": "EVENT ", "long": "All City Event 1"}, {"category": "Interop", "tg": 13552, "short": "EVENT ", "long": "All City Event 2"}, {"category": "Interop", "tg": 13584, "short": "SAFEVT ", "long": "Public Safety Event 1"}, {"category": "Interop", "tg": 13616, "short": "SAFEVT ", "long": "Public Safety Event 2"}, {"category": "Interop", "tg": 13648, "short": "SAFEVT ", "long": "Public Safety Event 3"}, {"category": "EMS-Tac", "tg": 944, "short": "SFFD EMS", "long": "EMS 1 Medic-Hospital Control 7"}, {"category": "EMS-Tac", "tg": 976, "short": "SFFD EMS", "long": "EMS 2 Medic-Hospital Control 8"}, {"category": "EMS-Tac", "tg": 15312, "short": "SFFD EMS", "long": "Ambulance non-emergency Control 9"}, {"category": "EMS-Tac", "tg": 15344, "short": "SFFD EMS", "long": "Private ambulance Control 10"}, {"category": "Fire Dispatch", "tg": 1008, "short": "SFFD-B", "long": "SFFD"}, {"category": "Fire Dispatch", "tg": 14800, "short": "SFFD-A", "long": "Dispatch Division 1 Control 1"}, {"category": "Fire Dispatch", "tg": 14832, "short": "SFFD-A", "long": "Dispatch Division 2 Control 2"}, {"category": "Fire Dispatch", "tg": 14864, "short": "SFFD-A", "long": "Dispatch Division 3 Control 3"}, {"category": "Fire-Talk", "tg": 14896, "short": "SFFD-A", "long": "Command - Greater Alarms - Control 4"}, {"category": "Fire-Talk", "tg": 14928, "short": "SFFD-A", "long": "Command - Greater Alarms - Control 5"}, {"category": "Fire-Talk", "tg": 14960, "short": "SFFD-A", "long": "Command - Greater Alarms - Control 6"}, {"category": "Fire-Tac", "tg": 14992, "short": "SFFD-A", "long": "Tactical Battalion 7"}, {"category": "Fire-Tac", "tg": 15024, "short": "SFFD-A", "long": "Tactical Battalion 8"}, {"category": "Fire-Tac", "tg": 15056, "short": "SFFD-A", "long": "Tactical Battalion 9"}, {"category": "Fire-Tac", "tg": 15088, "short": "SFFD-A1", "long": "Tactical Battalion 10"}, {"category": "Fire-Tac", "tg": 15120, "short": "SFFD-A1", "long": "Tactical Battalion 1"}, {"category": "Fire-Tac", "tg": 15152, "short": "SFFD-A1", "long": "Tactical Battalion 2"}, {"category": "Fire-Tac", "tg": 15184, "short": "SFFD-A1", "long": "Tactical Battalion 3"}, {"category": "Fire-Tac", "tg": 15216, "short": "SFFD-A1", "long": "Tactical Battalion 4"}, {"category": "Fire-Tac", "tg": 15248, "short": "SFFD-A1", "long": "Tactical Battalion 5"}, {"category": "Fire-Tac", "tg": 15280, "short": "SFFD-A1", "long": "Tactical Battalion 6"}, {"category": "Fire-Talk", "tg": 15440, "short": "SFFD-B", "long": "Prevention"}, {"category": "Fire-Talk", "tg": 15472, "short": "SFFD-B", "long": "Auxiliary Water Supply System"}, {"category": "Fire-Talk", "tg": 15760, "short": "SFFD-B1", "long": "Bureau of Equipment"}, {"category": "Fire-Talk", "tg": 15792, "short": "SFFDB-1", "long": "Training"}, {"category": "Emergency Ops", "tg": 17424, "short": "OES", "long": "Office of Emergency Services "}, {"category": "Emergency Ops", "tg": 17456, "short": "OES", "long": "Office of Emergency Services "}, {"category": "Emergency Ops", "tg": 17488, "short": "OES ADMI", "long": "Office of Emergency Services Admi"}, {"category": "Law Tac", "tg": 16, "short": "TAC ", "long": "Tactical 7"}, {"category": "Law Tac", "tg": 48, "short": "TAC ", "long": "Tactical 8"}, {"category": "Law Tac", "tg": 80, "short": "NARC", "long": "Narcotics 2"}, {"category": "Law Tac", "tg": 112, "short": "NARC", "long": "Narcotics 3"}, {"category": "Law Tac", "tg": 144, "short": "NARC", "long": "Narcotics 4"}, {"category": "Law Tac", "tg": 176, "short": "NARC", "long": "Narcotics 5"}, {"category": "Law Tac", "tg": 208, "short": "SID ", "long": "Special Investigations Division 2"}, {"category": "Law Tac", "tg": 240, "short": "VICE ", "long": "Vice 1"}, {"category": "Law Talk", "tg": 272, "short": "COMMAN", "long": "Command"}, {"category": "Law Dispatch", "tg": 12848, "short": "SFPD A", "long": "Dispatch Company A B J TI Central Southern"}, {"category": "Law Talk", "tg": 12880, "short": "SFPD A", "long": "Service Company A B J TI"}, {"category": "Law Dispatch", "tg": 12912, "short": "SFPD A", "long": "Dispatch Company C D Bayview Mission"}, {"category": "Law Talk", "tg": 12944, "short": "SFPD A", "long": "Service Company C D"}, {"category": "Law Dispatch", "tg": 12976, "short": "SFPD A", "long": "Dispatch Company E F Northern Park"}, {"category": "Law Talk", "tg": 13008, "short": "SFPD A", "long": "Service Company E F"}, {"category": "Law Dispatch", "tg": 13040, "short": "SFPD A", "long": "Dispatch Company G H I Richmond Ingleside Taraval"}, {"category": "Law Talk", "tg": 13072, "short": "SFPD A", "long": "Service Company G H I"}, {"category": "Law Dispatch", "tg": 13104, "short": "SFPD A", "long": "Dispatch spare"}, {"category": "Law Dispatch", "tg": 13136, "short": "SFPD A1", "long": "Dispatch spare"}, {"category": "Law Talk", "tg": 13168, "short": "SFPD A1", "long": "PAT Muni Tac Traffic"}, {"category": "Law Dispatch", "tg": 13200, "short": "SFPD A1", "long": "Dispatch spare"}, {"category": "Law Talk", "tg": 13232, "short": "SFPD A1", "long": "Station Service A B E F J TI"}, {"category": "Law Talk", "tg": 13264, "short": "SFPD A1", "long": "Station Service C D G H I"}, {"category": "Law Talk", "tg": 13296, "short": "PAROL", "long": ""}, {"category": "Law Tac", "tg": 13808, "short": "TAC ", "long": "Tactical 1 Administration"}, {"category": "Law Tac", "tg": 13840, "short": "TAC ", "long": "Tactical 2"}, {"category": "Law Tac", "tg": 13872, "short": "TAC ", "long": "Tactical 3"}, {"category": "Law Tac", "tg": 13904, "short": "TAC ", "long": "Tactical 4"}, {"category": "Law Tac", "tg": 13936, "short": "TAC ", "long": "Tactical 5"}, {"category": "Law Talk", "tg": 13968, "short": "TAC ", "long": "Tactical 6 (Mounted-Honda-Air-Sea)"}, {"category": "Law Tac", "tg": 14000, "short": "TAC ", "long": "Tactical 7"}, {"category": "Law Tac", "tg": 14032, "short": "TAC ", "long": "Tactical 8"}, {"category": "Law Talk", "tg": 14064, "short": "PDB 1", "long": "Robbery Apprehension Team"}, {"category": "Law Tac", "tg": 14096, "short": "TAC 1", "long": "Tactical 10"}, {"category": "Law Tac", "tg": 14128, "short": "TAC 1", "long": "Tactical 11"}, {"category": "Law Tac", "tg": 14160, "short": "TAC 1", "long": "Tactical 12"}, {"category": "Law Tac", "tg": 14192, "short": "TAC 1", "long": "Tactical 13"}, {"category": "Law Tac", "tg": 14224, "short": "POL-EVEN", "long": "Tactical 14 (Event)"}, {"category": "Law Tac", "tg": 14256, "short": "TAC 1", "long": "Tactical 15"}, {"category": "Law Talk", "tg": 14288, "short": "NARC", "long": "Narcotics 1 Administration"}, {"category": "Law Talk", "tg": 14544, "short": "INV", "long": "Investigations 1 Administration"}, {"category": "Law Talk", "tg": 14576, "short": "SID ", "long": "Special Investigations Division 1"}, {"category": "Law Talk", "tg": 14704, "short": "TRAIN ", "long": "Training 1"}, {"category": "Law Talk", "tg": 14736, "short": "TRAIN ", "long": "Training 2"}, {"category": "Law Dispatch", "tg": 17840, "short": "SFSU ", "long": ""}, {"category": "Law Tac", "tg": 17872, "short": "SFSU ", "long": ""}, {"category": "Law Tac", "tg": 17904, "short": "SFSU ", "long": ""}, {"category": "Law Talk", "tg": 15856, "short": "SFSO A", "long": "Jail 1"}, {"category": "Law Talk", "tg": 15888, "short": "SFSO A", "long": "Jail 2"}, {"category": "Law Talk", "tg": 15920, "short": "SFSO A", "long": "Jail 5 West Law Talk "}, {"category": "Law Talk", "tg": 15952, "short": "SFSO A", "long": "Jail 5 East Law Talk "}, {"category": "Law Talk", "tg": 15984, "short": "SFSO A", "long": "Jail 8"}, {"category": "Law Talk", "tg": 16016, "short": "SFSO A", "long": "Jail 9"}, {"category": "Law Talk", "tg": 16048, "short": "SFSO A", "long": "Classification Unit/SBBS"}, {"category": "Law Dispatch", "tg": 16080, "short": "SFSO A", "long": "City Hall Patrol Dispatch"}, {"category": "Security", "tg": 16112, "short": "SFSO A", "long": "YGC/Laguna Honda Security"}, {"category": "Security", "tg": 16144, "short": "SFSO A1", "long": "HOJ Courts/Civil Courts"}, {"category": "Law Talk", "tg": 16176, "short": "SFSO A1", "long": "Transportation SWAP SFGH"}, {"category": "Law Talk", "tg": 16208, "short": "SFSO A1", "long": "Law Talk - Future"}, {"category": "Law Tac", "tg": 16240, "short": "SFSO A1", "long": "Emergency Services Unit"}, {"category": "Law Talk", "tg": 16272, "short": "SFSO A1", "long": "Station Transfers / Evictions / Field Support & Services"}, {"category": "Security", "tg": 49200, "short": "SGH-I", "long": "SF General Hospital Patrol"}, {"category": "Multi-Dispatch", "tg": 18032, "short": "UCSF ", "long": ""}, {"category": "Multi-Dispatch", "tg": 18064, "short": "UCSF ", "long": ""}, {"category": "Multi-Dispatc", "tg": 18096, "short": "UCSF ", "long": ""}];

    function decodeTalkGroup(tg) {
	var base_tg = tg - (tg % 16);

	for (var i = 0; i < tgs.length; i++) {
	    if (tgs[i].tg == base_tg) {
		return tgs[i];
	    }
	}
	return null;
    }


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

	    var tgent = decodeTalkGroup(tg);

	    if (tgent) {
		this.channels[i].description = tg + "/" + tgent.category + "/" + tgent.long;
	    } else {
		this.channels[i].description = tg;
	    }
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
