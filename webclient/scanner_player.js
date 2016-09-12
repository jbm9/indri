var scanner_player = (function() {
  function ScannerPlayer() {
      var backlog = []; // enqueued-but-unavailable files
      var queue = []; // actual playlist


      var playing = false;

      var sysac = audioContext = window.AudioContext || window.webkitAudioContext;
      var context = new sysac();

      var uidiv = null; // <div> for our UI

      var talkgroups = {}; // our talkgroup database

      var base_url = "http://localhost/"; // base of all WAV urls

      this.setBaseURL = function(u) { base_url = u; }

      // kludge to allow this to work in ios
      function ios_unlock_sound(event) {
	  var buffer = context.createBuffer(1, 1, 22050);    
	  var source = context.createBufferSource();    
	  source.buffer = buffer;    
	  source.connect(context.destination);    
	  source.noteOn(0);    
	  window.removeEventListener("touchend", ios_unlock_sound, false);
      }
      window.addEventListener("touchend", ios_unlock_sound, false);

      var play = function(entry) {
	  var url = base_url + entry.filename;

	  set_current_tg("(loading) " + entry.tg);

	  console.info("play: " + url);
	  playing = true;

	  var request = new XMLHttpRequest();

	  request.open("GET", url, true);
	  request.responseType = "arraybuffer";

	  request.onload = function() {
	      var bytes = request.response;

              context.decodeAudioData(bytes, function(buffer) {
		  try {
		      source.stop(); // just in case
		  } catch(e) { }
		  source = context.createBufferSource();
		  source.onended = play_next;
		  source.buffer = buffer;

		  source.connect(context.destination);
		  source.start(0);
		  set_current_tg(entry.tg);
              },
					   function(e) { alert("Audio decode error: " + e) }
					  );
	  };
	  request.send();
      };


      var play_next = function() {
	  console.log("play_next: " + this );
	  if (queue.length) {
	      play(queue.shift());
	  } else {
	      playing = false;
	      set_current_tg(null);
	  }
      }

      
      this.enqueue = function(tg,filename) {
	  console.log("Enqueue at " + queue.length + ": " + filename);

	  var entry = { "filename": filename,
			"tg": tg,
			"available": false };

	  backlog.push(entry);
      };

      this.available = function(filename) {
	  var entry_to_play = null;


	  console.log("available: " + filename);

	  for (var i = 0; !entry_to_play && i < backlog.length; i++) {
	      if (filename == backlog[i].filename) {
		  backlog[i].available = true;
		  entry_to_play = backlog[i];
		  var newbacklog = backlog.filter(function(e,i,a) { return !e.available;});
		  backlog = newbacklog;
	      }
	  }


	  if (entry_to_play) {
	      queue.push(entry_to_play);
	      if (!playing) play_next();
	  }	  
      }


      function decode_tg(tg) {
	  var e = talkgroups[tg];
	  if (e)
	      return e.short + "/" + e.long;
	  return "(unk)";
      }

      var set_current_tg = function(s) {
	  var curtg = uidiv.find(".current_tg");
	  console.log(curtg);
	  if (null == s) {
	      curtg.text("-idle-");
	      curtg.css("background-color", "#ccc")
	  } else {
	      var decode = decode_tg(s);
	      curtg.text("TG-" + parseInt(s).toString(16) + " " + decode);
	      curtg.css("background-color", "#ecc")
	  }
      }



      var setup_ui = function() {
	  if (!uidiv) return;

	  var tgdisplay = document.createElement("div");
	  var newlabel = document.createElement("span");
	  newlabel.textContent = "Now playing:";
	  tgdisplay.appendChild(newlabel);

	  var curtg = document.createElement("span");
	  curtg.classList.add("current_tg");
	  tgdisplay.appendChild(curtg);

	  uidiv.append(tgdisplay);


	  set_current_tg(null);

      }


      this.initUI = function(uidiv_in) {
	  uidiv = uidiv_in;

	  setup_ui();
      }


      this.initTalkGroups = function(tgs_in) {
	  var i;
	  for (i = 0; i < tgs_in.length; i++) {
	      var e = tgs_in[i];
	      talkgroups[e.tg] = e;
	  }
      };
  };


    var sp = new ScannerPlayer();
    return sp;
})();
