
import Qt 4.7

import 'config.js' as Config
import 'util.js' as Util

SelectableItem {
    id: podcastItem

    // Show context menu when single-touching the count or cover art
    singlePressContextMenuLeftBorder: titleBox.x

    Text {
        id: counterText
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.rightMargin: 5
        text: formatCount(modelData.qnew, modelData.qdownloaded)
        color: "white"
        width: Config.iconSize * 1.9
        font.pixelSize: podcastItem.height * .4
        horizontalAlignment: Text.AlignRight
        visible: !spinner.visible

        function formatCount(qnew, qdownloaded) {
            var s = ''

            if (qdownloaded) {
                s += qdownloaded
            }

            if (qnew) {
                s += '<sup><font color="yellow">+' + qnew + '</font></sup>'
            }

            return s
        }
    }

    Image {
        id: spinner
        anchors {
            verticalCenter: parent.verticalCenter
            right: cover.left
            rightMargin: Config.smallSpacing
        }
        source: 'artwork/spinner.png'
        visible: modelData.qupdating
        smooth: true

        RotationAnimation {
            target: spinner
            property: 'rotation'
            direction: RotationAnimation.Clockwise
            from: 0
            to: 360
            duration: 1200
            running: spinner.visible
            loops: Animation.Infinite
        }
    }

    Image {
    	id: cover

        visible: modelData.qcoverurl != ''
        source: Util.formatCoverURL(modelData)
        asynchronous: true
        width: podcastItem.height * .8
        height: width
        sourceSize.width: width
        sourceSize.height: height

        anchors {
            verticalCenter: parent.verticalCenter
            left: counterText.right
            leftMargin: Config.smallSpacing
        }
    }

    Text {
        id: titleBox

        text: modelData.qtitle
        color: "white"

        anchors {
            verticalCenter: parent.verticalCenter
            left: cover.visible?cover.right:cover.left
            leftMargin: Config.smallSpacing
            right: parent.right
            rightMargin: Config.smallSpacing
        }

        font.pixelSize: podcastItem.height * .35
        elide: Text.ElideRight
    }
}

