/*
 * This javascript file uses the YouTube iframe API to start a video and enable
 * an input element once it has ended.
 */
var tag = document.createElement('script');
tag.src = "https://www.youtube.com/iframe_api";
var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

var player;
function onYouTubeIframeAPIReady() {
  var trainedInput = document.getElementById("trained-input");
  if (trainedInput) {
    trainedInput.disabled = true;
  }
  player = new YT.Player('ytplayer', {
    events: {
      'onReady': onPlayerReady,
      'onStateChange': onPlayerStateChange
    }
  });
}

function onPlayerReady(event) {
  event.target.setVolume(100);
}

function onPlayerStateChange(event) {
  if (event.data == YT.PlayerState.ENDED) {
    var trainedInput = document.getElementById("trained-input");
    if (trainedInput) {
      trainedInput.disabled = false;
    }
  }
}
