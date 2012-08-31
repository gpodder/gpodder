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
        var wrapper = document.createElement('p');

        wrapper.setAttribute('class', 'listwrapper');

        if(episode.mime_type.indexOf('video') == 0)
            img.setAttribute('src', '/static/images/video.png');
        else if(episode.mime_type.indexOf('audio') == 0)
            img.setAttribute('src', '/static/images/audio.png');
        wrapper.appendChild(img);
        //img.setAttribute('class', 'ui-li-icon');
        var title = document.createElement('h3');
        title.appendChild(document.createTextNode(episode.title));
        var description = document.createElement('p');
        description.appendChild(document.createTextNode(episode.description));

        a.setAttribute('gpodder:episode', JSON.stringify(episode));
        a.setAttribute('data-rel', 'dialog');
        a.setAttribute('data-transition', 'pop');

        a.href = '#episode_details';
        a.onclick = function() {
            gPodder.selectEpisode(this);
            gPodder.currentlySelectedEpisode = this;
        };
        a.appendChild(wrapper);
        a.appendChild(title);
        a.appendChild(description);

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

        if(episode.mime_type.indexOf("audio") == 0)
            content += '<div align="center"><audio id="episode_player" width="100%" controls="controls"><source src="' + episode.url + '" type="' + episode.mime_type + '" /></audio></div><br/>';
        else if(episode.mime_type.indexOf("video") == 0)
            content += '<video width="100%" id="episode_player" controls="controls"><source src="' + episode.url + '" type="' + episode.mime_type + '" /></video><br/>';

        // TODO: Add more fields in the dialog box (Pubdate, etc.)
        var published = new Date(episode.published * 1000)
        content += '<strong>' + episode.title + '</strong>';

        //content += '<div data-role="collapsible">';
        //content += '<h3>Details</h3>';

        content += '<p>' + episode.description + '</p>';
        content += '<strong>Released: </strong>' + published.toDateString() + '<br/>';
        content += '<strong>Time: </strong>' + published.toTimeString() + '<br/>';
        content += '<strong>Size: </strong>' + gPodder.bytesToSize(episode.file_size) + '<br/>';
        content += '<strong>Link: </strong><a href="' + episode.link + '" rel="external">' + episode.link + '</a><br/>';
        //content += '</div>'; // End collapsible
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
            $.post('/podcast/save', function() {
                console.log("POSTED");
            })
        });

        // TODO: Mark the current position
        $('#episode_player').bind('pause', function() {
            console.log("paused episode: " + episode.url + " at " + this.currentTime);
        });

    },
    bytesToSize: function(bytes) {
        var sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        if (bytes == 0) return 'n/a';
        var i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
        return Math.round(bytes / Math.pow(1024, i), 2) + ' ' + sizes[i];
    }
};

