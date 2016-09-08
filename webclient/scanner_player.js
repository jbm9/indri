var scanner_player = (function() {
  function ScannerPlayer() {
      var queue = [];


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

      var play = function(url) {
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

      
      this.enqueue = function(url) {
	  console.log("Enqueue at " + queue.length + ": " + url);
	  queue.push(url);
	  if (!playing) play_next();
      };
  };


    var sp = new ScannerPlayer();
    return sp;
})();
