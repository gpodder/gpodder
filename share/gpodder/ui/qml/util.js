
function formatDuration(duration) {
    if (duration !== 0 && !duration) {
        return ''
    }

    var h = parseInt(duration / 3600) % 24
    var m = parseInt(duration / 60) % 60
    var s = parseInt(duration % 60)

    var hh = h > 0 ? (h < 10 ? '0' + h : h) + ':' : ''
    var ms = (m < 10 ? '0' + m : m) + ':' + (s < 10 ? '0' + s : s)

    return hh + ms
}

function formatPosition(position,duration) {
  return formatDuration(position) + " / " + formatDuration(duration)
}
