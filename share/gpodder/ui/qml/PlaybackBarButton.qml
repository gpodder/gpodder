
import QtQuick 1.1

import 'config.js' as Config

Image {
    signal clicked()
    property alias pressed: mouseArea.pressed

    width: 64 * Config.scale
    height: 64 * Config.scale

    MouseArea {
        id: mouseArea
        property real accumulatedDistance: 0
        property real lastX: 0
        property real lastY: 0
        anchors.fill: parent
        onClicked: parent.clicked()
        onPressed: {
            console.log('pressed');
            accumulatedDistance = 0;
            lastX = mouse.x;
            lastY = mouse.y;
        }
        onPositionChanged: {
            accumulatedDistance += Math.sqrt(Math.pow(lastX - mouse.x, 2) + Math.pow(lastY - mouse.y, 2));
            if (accumulatedDistance > 120) {
                // Allow "scrubbing" with the button
                accumulatedDistance = 0;
                parent.clicked();
            }
            lastX = mouse.x;
            lastY = mouse.y;
        }
    }

    Rectangle {
        anchors.fill: parent
        color: 'black'
        radius: Config.smallSpacing
        opacity: mouseArea.pressed?.5:0
    }
}

