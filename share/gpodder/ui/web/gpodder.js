gPodder = {
    /* XXX: Partially ugly. Some parts would be shorter with JQuery. */

    currentlySelectedPodcast: null,
    currentlySelectedEpisode: null,

    quote: function(str) {
        var s = String(str);
        s = s.replace(/&/g, '&amp;');
        s = s.replace(/</g, '&lt;');
        s = s.replace(/>/g, '&gt;');
        s = s.replace(/"/g, '&quot;');
        return s;
    },

    url: {
        podcasts: '/json/podcasts.json',
        episodes: function(podcast) {
            return '/json/podcast/' + podcast.id + '/episodes.json';
        },
    },

    createEpisode: function(episode) {
		var li = document.createElement('li');
		var a = document.createElement('a');
		var img = document.createElement('img');

		if(episode.mime_type.indexOf('video') == 0)
			img.setAttribute('src', '/static/images/video.png');
		else if(episode.mime_type.indexOf('audio') == 0)
			img.setAttribute('src', '/static/images/music.png');

			//img.setAttribute('class', 'ui-li-icon');
		var title = document.createElement('h3');
		var duration = document.createElement('span');
		duration.setAttribute('class', 'ui-li-aside');
		var pubdate = new Date(episode.published * 1000);
		duration.appendChild(document.createTextNode(pubdate.toDateString()));

		title.appendChild(document.createTextNode(episode.title));
		var description = document.createElement('p');
		description.appendChild(document.createTextNode(episode.description));

		a.setAttribute('gpodder:episode', JSON.stringify(episode));
		a.setAttribute('data-rel', 'dialog');
		a.setAttribute('data-transition', 'slide');
		a.href = '#episode_details';
		a.onclick = function() {
			gPodder.selectEpisode(this);
			gPodder.currentlySelectedEpisode = this;
		};
		a.appendChild(img);
		a.appendChild(title);
		a.appendChild(description);
		a.appendChild(duration);
			
		li.appendChild(a);
		return li;
    },

    createPodcast: function(podcast) {
        var li = document.createElement('li');
		var img = document.createElement('img');
		img.setAttribute('src', podcast.cover_url);
		var title = document.createElement('h3');
		title.appendChild(document.createTextNode(podcast.title));
		var description = document.createElement('p');
		description.appendChild(document.createTextNode(podcast.description));

        var a = document.createElement('a');
        a.setAttribute('gpodder:podcast', JSON.stringify(podcast));
        a.href = '#episodes_page';
        a.onclick = function() {
            gPodder.selectPodcast(this);
            gPodder.currentlySelectedPodcast = this;
        };
		a.appendChild(img);
		a.appendChild(title);
		a.appendChild(description);	

        li.appendChild(a);
        return li;
    },

    init: function() {
	$.getJSON(gPodder.url.podcasts, function(data) {
		$('#podcasts').html('');
		$.each(data, function() {
			$('#podcasts').append(gPodder.createPodcast(this));
		})
                $('#podcasts').listview('refresh');
	});
    },

    selectPodcast: function(li) {
        var podcast = JSON.parse(li.getAttribute('gpodder:podcast'));
	    $.getJSON(gPodder.url.episodes(podcast), function(data) {
            $('#episodes_title').html(podcast.title);
		    $('#episodes').html('');
            $.each(data, function() {
                $('#episodes').append(gPodder.createEpisode(this));
            })
	        $('#episodes').listview('refresh');
	    });
    },

    selectEpisode: function(li) {
        var episode = JSON.parse(li.getAttribute('gpodder:episode'));
        var content = '';
        var media_url = '';
		
		content += '<strong>' + episode.title + '</strong>';
		content += '<p>' + episode.description + '</p>';
		if(episode.mime_type.indexOf("audio") == 0)            
			content += '<div align="center"><audio id="episode_player" width="100%" controls="controls"><source src="' + episode.url + '" type="' + episode.mime_type + '" /></audio></div><br/>';
		else if(episode.mime_type.indexOf("video") == 0)	
			content += '<video width="100%" id="episode_player" controls="controls"><source src="' + episode.url + '" type="' + episode.mime_type + '" /></video><br/>';

		// TODO: Add more fields in the dialog box (Pubdate, etc.)

		$('#episode_details_title').text(episode.title);
		$('#episode_details_content').html(content);

		// Pause playback if the dialog is closed	
		$('#episode_details').bind('pagebeforehide', function() {
			$('#episode_player').get(0).pause();
		});
		// Start the player at the last saved position
		$('#episode_player').bind('loadedmetadata', function() {
			this.currentTime = episode.current_position;
		});

		// TODO: Mark the episode as played
		$('#episode_player').bind('play', function() {
			console.log("played episode: " + episode.url);
		});

		// TODO: Mark the current position
		$('#episode_player').bind('pause', function() {
			console.log("paused episode: " + episode.url + " at " + this.currentTime);
		});

    },

};

