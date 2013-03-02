
import QtQuick 1.1

import org.gpodder.qmlui 1.0

import 'config.js' as Config
import 'util.js' as Util

Item {
    id: root

    property real progress: 0
    property int duration: 0
    property real mousepos: 0
    property bool seekButtonPressed: false
    property real seekButtonPosition: 0
    property bool isPlaying: false
    property bool overrideDisplay: false
    property string overrideCaption: ''
    signal setProgress(real progress)

    height: 64 * Config.scale

    BorderImage {
        anchors {
            verticalCenter: parent.verticalCenter
            left: parent.left
            right: parent.right
        }

        height: 9

        source: 'artwork/slider-bg.png'

        Rectangle {
            id: seekTimePreviewBackground

            anchors.fill: seekTimePreview
            color: 'black'
            opacity: seekTimePreview.opacity*.8
            radius: Config.largeSpacing
            smooth: true
        }

        Label {
            id: seekTimePreview
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.top
            anchors.bottomMargin: Config.largeSpacing * 12
            text: {
                if (root.overrideDisplay || !mouseArea.pressed) {
                    ' ' + root.overrideCaption + ' '
                } else {
                    ' ' + Util.formatDuration(root.mousepos*duration) + ' '
                }
            }
            font.pixelSize: 50 * Config.scale
            horizontalAlignment: Text.AlignHCenter
            color: 'white'
            opacity: mouseArea.pressed || root.overrideDisplay
            scale: opacity?1:.5
            transformOrigin: Item.Bottom

            Behavior on opacity { PropertyAnimation { } }
            Behavior on scale { PropertyAnimation { } }
        }

        border {
            top: 2
            left: 2
            right: 2
            bottom: 2
        }

        BorderImage {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: parent.border.left
            anchors.topMargin: parent.border.top

            width: Math.max(1, (parent.width-parent.border.left-parent.border.right) * Math.max(0, Math.min(1, root.progress)))
            source: 'artwork/slider-fg.png'
            clip: true

            Image {
                visible: root.isPlaying || root.progress < 1
                source: 'artwork/slider-dot.png'
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.right
                anchors.leftMargin: -width
            }
        }

        BorderImage {
            opacity: mouseArea.pressed || root.seekButtonPressed
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: parent.border.left
            anchors.topMargin: parent.border.top

            width: Math.max(1, (parent.width-parent.border.left-parent.border.right) * Math.max(0, Math.min(1, (mouseArea.pressed?root.mousepos:root.seekButtonPosition))))
            source: 'artwork/slider-seeking-fg.png'
            clip: true

            Image {
                source: 'artwork/slider-seeking-dot.png'
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.right
                anchors.leftMargin: -width
            }
        }

    }
    MouseArea {
        id: mouseArea

        /**
         * Fix to prevent page switch gesture on Sailfish Silica, see
         * https://lists.sailfishos.org/pipermail/devel/2013-March/000022.html
         **/
        drag {
            axis: Drag.XAxis
            target: Item {}
        }

        anchors.fill: parent
        onClicked: {
            root.setProgress(mouse.x / root.width)
        }
        onPositionChanged: {
            root.mousepos = (mouse.x/root.width)
            if (root.mousepos < 0) root.mousepos = 0
            if (root.mousepos > 1) root.mousepos = 1
        }
        onPressed: {
            root.mousepos = (mouse.x/root.width)
            if (root.mousepos < 0) root.mousepos = 0
            if (root.mousepos > 1) root.mousepos = 1
        }
    }
}

