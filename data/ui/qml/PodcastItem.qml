
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
        width: Config.iconSize * 1.9
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
        source: 'artwork/cover-shadow.png'
        visible: modelData.qcoverurl != ''

        height: podcastItem.height * .8
        width: podcastItem.height * .8

        anchors {
            verticalCenter: parent.verticalCenter
            left: counterText.right
            leftMargin: Config.smallSpacing
        }

        Image {
            source: (modelData.qcoverurl != '')?('image://cover/'+escape(modelData.qcoverfile)+'|'+escape(modelData.qcoverurl)+'|'+escape(modelData.qurl)):''
            asynchronous: true
            width: parent.width * .85
            height: parent.height * .85
            sourceSize.width: width
            sourceSize.height: height
            anchors.centerIn: parent

            Image {
                id: spinner
                anchors.centerIn: parent
                width: parent.width * 1.3
                height: parent.height * 1.3
                source: 'artwork/spinner.png'
                opacity: modelData.qupdating?1:0

                Behavior on opacity { PropertyAnimation { } }

                RotationAnimation {
                    target: spinner
                    property: 'rotation'
                    direction: RotationAnimation.Clockwise
                    from: 0
                    to: 360
                    duration: 1200
                    running: modelData.qupdating
                    loops: Animation.Infinite
                }
            }
        }
    }

    Text {
        id: titleBox

        property int titleSize: podcastItem.height * .35
        property int subtitleSize: podcastItem.height * .25

        text: '<font style="font-size: '+titleSize+'px;">' + modelData.qtitle + '</font>'+(modelData.qdescription?('<br><font style="font-size: '+subtitleSize+'px; color: #aaa;">' + modelData.qdescription + '</font>'):'')
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

