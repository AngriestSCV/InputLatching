import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." 1.0

Item {
    function fmtBytes(n) {
        if (n < 1024) return n + " B"
        if (n < 1048576) return (n / 1024).toFixed(1) + " KB"
        return (n / 1048576).toFixed(1) + " MB"
    }

    function fmtUptime(secs) {
        var s = Math.floor(secs)
        var m = Math.floor(s / 60)
        var h = Math.floor(m / 60)
        if (h > 0) return h + "h " + (m % 60) + "m " + (s % 60) + "s"
        if (m > 0) return m + "m " + (s % 60) + "s"
        return s + "s"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        // ── Server config card ────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: rjoyConfigCol.implicitHeight + 20
            color: Theme.clrSurface; radius: 10
            border.color: Theme.clrBorder; border.width: 1

            ColumnLayout {
                id: rjoyConfigCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                spacing: 8

                SectionLabel { text: "SERVER CONFIGURATION" }

                RowLayout {
                    spacing: 6
                    Label { text: "Host"; color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 40 }
                    TextField {
                        id: rjoyHost
                        text: "0.0.0.0"
                        Layout.fillWidth: true
                        color: Theme.clrText
                        font.pixelSize: 12
                        background: Rectangle {
                            color: palette.base
                            border.color: rjoyHost.activeFocus ? Theme.clrAccent : Theme.clrBorder
                            border.width: 1; radius: 6
                        }
                        leftPadding: 8; rightPadding: 8
                    }
                }

                RowLayout {
                    spacing: 6
                    Label { text: "Port"; color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 40 }
                    TextField {
                        id: rjoyPort
                        text: "8765"
                        Layout.fillWidth: true
                        color: Theme.clrText
                        font.pixelSize: 12
                        validator: IntValidator { bottom: 1; top: 65535 }
                        background: Rectangle {
                            color: palette.base
                            border.color: rjoyPort.activeFocus ? Theme.clrAccent : Theme.clrBorder
                            border.width: 1; radius: 6
                        }
                        leftPadding: 8; rightPadding: 8
                    }
                }
            }
        }

        // ── Transport controls ────────────────────────────────────────────────
        RowLayout {
            spacing: 8
            Layout.fillWidth: true
            AppButton {
                text: "▶  Start Server"
                tint: Theme.clrGreen
                Layout.fillWidth: true
                onClicked: rjoyBridge.startServer(rjoyHost.text, parseInt(rjoyPort.text))
            }
            AppButton {
                text: "■  Stop Server"
                tint: Theme.clrRed
                Layout.fillWidth: true
                onClicked: rjoyBridge.stopServer()
            }
        }

        AppButton {
            text: "Open in Browser"
            Layout.fillWidth: true
            enabled: rjoyBridge.running
            opacity: rjoyBridge.running ? 1.0 : 0.4
            onClicked: Qt.openUrlExternally("http://" + rjoyHost.text + ":" + rjoyPort.text)
        }

        // ── Status card ───────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: rjoyStatusCol.implicitHeight + 20
            color: Theme.clrSurface; radius: 10
            border.color: Theme.clrBorder; border.width: 1

            ColumnLayout {
                id: rjoyStatusCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                spacing: 8

                SectionLabel { text: "STATUS" }

                RowLayout {
                    spacing: 8
                    StatusPill {
                        active: rjoyBridge.running
                        label: rjoyBridge.running ? "Running" : "Stopped"
                        activeColor: Theme.clrGreen
                    }
                    StatusPill {
                        active: rjoyBridge.clientCount > 0
                        label: rjoyBridge.clientCount + (rjoyBridge.clientCount === 1 ? " client" : " clients")
                        activeColor: Theme.clrAccent
                    }
                }

                Divider {}

                RowLayout {
                    spacing: 6
                    Label { text: "URL";      color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 60 }
                    Label {
                        text: rjoyBridge.running
                              ? "http://" + rjoyHost.text + ":" + rjoyPort.text
                              : "—"
                        color: Theme.clrText; font.pixelSize: 12; font.family: "monospace"
                    }
                }
                RowLayout {
                    spacing: 6
                    Label { text: "Uptime";   color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 60 }
                    Label {
                        text: rjoyBridge.running ? fmtUptime(rjoyBridge.uptime) : "—"
                        color: Theme.clrText; font.pixelSize: 12
                    }
                }
                RowLayout {
                    spacing: 6
                    Label { text: "Sent";     color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 60 }
                    Label {
                        text: rjoyBridge.running ? fmtBytes(rjoyBridge.bytesSent) : "—"
                        color: Theme.clrText; font.pixelSize: 12
                    }
                }
                RowLayout {
                    spacing: 6
                    Label { text: "Received"; color: Theme.clrDim; font.pixelSize: 12; Layout.preferredWidth: 60 }
                    Label {
                        text: rjoyBridge.running ? fmtBytes(rjoyBridge.bytesReceived) : "—"
                        color: Theme.clrText; font.pixelSize: 12
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
