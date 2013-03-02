
import QtQuick 1.1
import com.nokia.meego 1.0

import '../../../../config.js' as Config

Item {
    id: pullDown
    clip: true

    signal refresh

    property string pullDownText: ''
    property string releaseText: ''
    property variant target
    property int threshold: 100
    property int lastMinY: 0
    property bool startedAtZero: false
    property bool wouldRefresh: (lastMinY < -threshold)
    property bool enabled: false

    Connections {
        target: pullDown.target

        onMovementStarted: {
            pullDown.lastMinY = 0;
            pullDown.startedAtZero = (pullDown.target.contentY === 0);
        }

        onContentYChanged: {
            if (pullDown.startedAtZero && pullDown.target.moving && !pullDown.target.flicking) {
                if (pullDown.target.contentY > 0) {
                    pullDown.startedAtZero = false;
                } else if (pullDown.target.contentY < pullDown.lastMinY) {
                    pullDown.lastMinY = pullDown.target.contentY;
                }
            }
        }

        onFlickStarted: {
            pullDown.startedAtZero = false;
        }

        onMovementEnded: {
            if (enabled && pullDown.startedAtZero && pullDown.target.contentY == 0 && pullDown.wouldRefresh) {
                pullDown.refresh();
            }
            pullDown.startedAtZero = false;
            pullDown.lastMinY = 0;
        }
    }

    visible: enabled && startedAtZero && pullDown.target.contentY < 0 && !pullDown.target.flicking
    height: -pullDown.target.contentY

    anchors {
        left: parent.left
        right: parent.right
    }

    Label {
        color: 'white'
        anchors.centerIn: parent
        text: pullDown.wouldRefresh?pullDown.releaseText:pullDown.pullDownText
        anchors.verticalCenter: parent.verticalCenter
    }
}

