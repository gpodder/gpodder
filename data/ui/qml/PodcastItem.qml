
import Qt 4.7

import 'config.js' as Config

SelectableItem {
    id: podcastItem

    Text {
        id: counterText
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.rightMargin: 5
        text: formatCount(modelData.qnew, modelData.qdownloaded)
        color: "white"
        width: Config.iconSize * 1.5
        font.pixelSize: podcastItem.height * .4
        horizontalAlignment: Text.AlignRight

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
    	id: cover
        source: 'podcastList/cover-shadow.png'

        height: podcastItem.height * .8
        width: podcastItem.height * .8
        smooth: true

        anchors {
            verticalCenter: parent.verticalCenter
            left: counterText.right
            leftMargin: Config.smallSpacing
        }

        Image {
            source: modelData.qcoverfile
            width: parent.width * .85
            height: parent.height * .85
            sourceSize.width: width
            sourceSize.height: height
            anchors.centerIn: parent
        }
    }

    Column {
        id: titleBox

        anchors {
            verticalCenter: parent.verticalCenter
            left: cover.right
            leftMargin: Config.smallSpacing
            right: parent.right
            rightMargin: Config.smallSpacing
        }

        ShadowText {
            id: titleText
            text: modelData.qtitle
            color: "white"
            anchors {
                left: parent.left
                right: parent.right
            }
            font.pixelSize: podcastItem.height * .35
        }

        ShadowText {
            id: descriptionText
            text: modelData.qupdating?"UPDATING...":modelData.qdescription
            visible: text != ''
            color: "#aaa"
            offsetX: -1
            offsetY: -1
            anchors {
                left: parent.left
                right: parent.right
            }
            font.pixelSize: podcastItem.height * .25
        }
    }
}

