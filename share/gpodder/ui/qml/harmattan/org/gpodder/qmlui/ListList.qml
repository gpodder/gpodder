
import QtQuick 1.1

ListView {
    property string headerText: ''
    property int headerHeight: 0

    property bool hasRefresh: false
    signal refresh

    PullDownHandle {
        enabled: parent.hasRefresh
        target: parent
        pullDownText: '↓ ' + _('Pull down to refresh') + ' ↓'
        releaseText: '↑ ' + _('Release to refresh') + ' ↑'
        onRefresh: parent.refresh()
    }
}
