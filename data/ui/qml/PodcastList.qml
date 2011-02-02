
import Qt 4.7

Rectangle {
    signal podcastSelected(variant podcast)
    signal podcastContextMenu(variant podcast)
    signal action(string action)

    id: rectangle
    color: "white"

    property alias model: listView.model

    Image {
        anchors.fill: parent
        source: 'podcastList/mask.png'
        sourceSize { height: 100; width: 100 }
    }

    Image {
        opacity: 1
        anchors.fill: parent
        source: 'podcastList/noise.png'
    }

    ListView {
        id: listView
        anchors.fill: parent
        anchors.rightMargin: (toolbarLandscape.opacity>0)?(toolbarLandscape.width+toolbarLandscape.anchors.rightMargin):(0)
        anchors.bottomMargin: (toolbar.opacity>0)?(toolbar.height+toolbar.anchors.bottomMargin):(0)

        delegate: PodcastItem {
            onPodcastSelected: rectangle.podcastSelected(podcast)
            onPodcastContextMenu: rectangle.podcastContextMenu(podcast)
        }
        snapMode: ListView.SnapToItem
    }

    Image {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: toolbar.top
        source: 'podcastList/toolbar_shadow_landscape.png'
        opacity: toolbar.opacity
    }

    ToolbarLandscape {
        id: toolbarLandscape
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        opacity: parent.width>parent.height?1:0

        anchors.rightMargin: -width+width*opacity
        Behavior on anchors.rightMargin { NumberAnimation { duration: 300 } }

        ToolbarButtonLandscape { source: 'podcastList/tb_refresh.png'; onClicked: rectangle.color = "#faa" }
        ToolbarButtonLandscape { source: 'podcastList/tb_add.png'; onClicked: rectangle.color = "#afa" }
        ToolbarButtonLandscape { source: 'podcastList/tb_search.png'; onClicked: rectangle.color = "#aaf" }
    }

    Toolbar {
        id: toolbar
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        opacity: parent.width<=parent.height?1:0

        anchors.bottomMargin: -height+height*opacity
        Behavior on anchors.bottomMargin { NumberAnimation { duration: 300 } }

        ToolbarButton { source: 'podcastList/tb_refresh.png'; onClicked: rectangle.action('refresh') }
        ToolbarButton { source: 'podcastList/tb_add.png'; onClicked: rectangle.color = "#afa" }
        ToolbarButton { source: 'podcastList/tb_search.png'; onClicked: rectangle.color = "#aaf" }
    }

}

