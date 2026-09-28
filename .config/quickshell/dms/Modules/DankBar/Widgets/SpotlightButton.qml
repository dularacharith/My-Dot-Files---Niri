import QtQuick
import qs.Common
import qs.Modules.Plugins
import qs.Services
import qs.Widgets

BasePill {
    id: root

    readonly property bool isActive: PopoutService.spotlightBarModal?.spotlightOpen ?? false

    content: Component {
        Item {
            implicitWidth: spotlightIcon.width
            implicitHeight: root.widgetThickness - root.horizontalPadding * 2

            DankIcon {
                id: spotlightIcon
                anchors.centerIn: parent
                name: "search"
                size: Theme.barIconSize(root.barThickness, -4, root.barConfig?.maximizeWidgetIcons, root.barConfig?.iconScale)
                color: root.isActive ? Theme.primary : Theme.widgetIconColor
            }
        }
    }

    onClicked: {
        PopoutService.toggleSpotlightBar();
    }
}
