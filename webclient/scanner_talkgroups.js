function ScannerTalkgroups() {
    var tgs = [];
    var tgIndex = {}; // tg => entry

    this.configUpdate = function(config) {
	tgs = config["talkgroups"];

	tgIndex = {}
	tgs.forEach(function(t) { tgIndex[t.tg] = t; });
    }

    this.lookup = function(tg) {
	return tgIndex[tg];
    }

    return this;
}
