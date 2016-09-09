var scanner_player = (function() {
  function ScannerPlayer() {
      var backlog = []; // enqueued-but-unavailable files
      var queue = []; // actual playlist


      var playing = false;

      var sysac = audioContext = window.Audiocontext || window.webkitAudioContext;
      var context = new sysac();

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

	  var url = "http://indri-testbed.s3-website-us-west-2.amazonaws.com/" + entry.filename;

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
  };


    var sp = new ScannerPlayer();
    return sp;
})();
