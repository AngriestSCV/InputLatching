import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: window
    width: 500
    height: 650
    title: "Latch Input Tool"
    visible: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8
        Layout.fillWidth: true

        // Device combobox + refresh
        RowLayout {
            spacing: 8
            ComboBox {
                id: deviceCombo
                model: bridge.deviceModel
                Layout.fillWidth: true
            }
            Button {
                text: "Refresh"
                onClicked: bridge.refreshDevices()
            }
        }

        RowLayout {
            spacing: 8
            Button { text: "Add Device"; onClicked: bridge.addDevice(deviceCombo.currentText) }
            Button { text: "Clear Devices"; onClicked: bridge.clearDevices() }
        }

        RowLayout {
            spacing: 8
            Button { text: "Start"; onClicked: bridge.start() }
            Button { text: "Stop"; onClicked: bridge.stop() }
            Button { text: "Set Trigger"; onClicked: bridge.beginSetTrigger() }
        }

        // State labels
        GroupBox {
            title: "State"
            Layout.fillWidth: true
            ColumnLayout {
                Label { text: "Trigger: " + bridge.trigger }
                Label { text: "Latched: " + bridge.latched }
                Label { text: "Trigger Held: " + (bridge.triggerHeld ? "True" : "False") }
                Label { text: "Devices: " + bridge.deviceCount }
                Label { text: "Running: " + (bridge.running ? "True" : "False") }
            }
        }

        // Log area
        GroupBox {
            id: logGroup
            title: "Log"
            Layout.fillHeight: true
            Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent
                Layout.fillWidth: true
                Layout.fillHeight: true

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    TextArea {
                        id: logArea
                        readOnly: true
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                    }
                }
                RowLayout {
                    spacing: 8
                    Layout.alignment: Qt.AlignCenter
                    Button { text: "Clear log"; onClicked: logArea.clear() }
                }
            }
        }
    }

    // append incoming log lines from bridge
    Connections {
        target: bridge
        function onLogAppended(message) {
            if (logArea.length > 0) logArea.append("\n" + message)
            else logArea.append(message)
            // auto-scroll: put cursor at end
            logArea.cursorPosition = logArea.length
        }
    }
}

