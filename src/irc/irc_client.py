from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtNetwork import QTcpSocket
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QLineEdit, QDialogButtonBox, QDialog, QLabel

class ConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Connect to IRC Server")

        self.layout = QVBoxLayout(self)

        self.host_label = QLabel("Host:", self)
        self.layout.addWidget(self.host_label)
        self.host_input = QLineEdit(self)
        self.host_input.setText("irc.rizon.net")
        self.layout.addWidget(self.host_input)

        self.port_label = QLabel("Port:", self)
        self.layout.addWidget(self.port_label)
        self.port_input = QLineEdit(self)
        self.port_input.setText("6667")
        self.layout.addWidget(self.port_input)

        self.nick_label = QLabel("Nickname:", self)
        self.layout.addWidget(self.nick_label)
        self.nick_input = QLineEdit(self)
        self.nick_input.setText("pyechat")
        self.layout.addWidget(self.nick_input)

        self.realname_label = QLabel("Real name:", self)
        self.layout.addWidget(self.realname_label)
        self.realname_input = QLineEdit(self)
        self.realname_input.setText("Pyechat: https://pyechat.github.io")
        self.layout.addWidget(self.realname_input)

        self.channel_label = QLabel("Channel:", self)
        self.layout.addWidget(self.channel_label)
        self.channel_input = QLineEdit(self)
        self.channel_input.setText("#pyechat")
        self.layout.addWidget(self.channel_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_values(self):
        return self.host_input.text(), int(self.port_input.text()), self.nick_input.text(), self.realname_input.text(), self.channel_input.text()
    
    def closeEvent(self, event):
        QApplication.quit()
    
class IRCClient(QObject):
    received_message = pyqtSignal(str)

    def __init__(self, server, port, nickname, realname, channel):
        super().__init__()

        self.socket = QTcpSocket()
        self.socket.readyRead.connect(self.on_ready_read)
        self.socket.errorOccurred.connect(self.on_error_occurred)

        self.server = server
        self.port = port
        self.nickname = nickname
        self.realname = realname
        self.channel = channel

    def connect_to_host(self):
        self.socket.connectToHost(self.server, self.port)
        self.send_command(f'NICK {self.nickname}')
        self.send_command(f'USER {self.nickname} 0 * :{self.realname}')

    def decode(self, bytes):
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        for encoding in encodings:
            try: 
                return bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("None of the encodings could decode the bytes.")

    def parse_message(self, message):
        parts = message.split()
        if len(parts) < 2:
            return None, None, []
        source = parts[0][1:] if parts[0].startswith(':') else None
        command = parts[1] if source else parts[0]
        args_start = 2 if source else 1
        args = []
        trailing_arg_start = None
        for i, part in enumerate(parts[args_start:], args_start):
            if part.startswith(':'):
                trailing_arg_start = i
                break
            else:
                args.append(part)
        if trailing_arg_start is not None:
            args.append(' '.join(parts[trailing_arg_start:])[1:])
        return source, command, args

    @pyqtSlot()
    def on_ready_read(self):
        while self.socket.canReadLine():
            line = self.socket.readLine().data()
            line = self.decode(line).strip()
            self.received_message.emit(line)

            source, command, args = self.parse_message(line)

            if command == 'NICK' and source.split('!')[0] == self.nickname:
                self.nickname = args[0]

            if command == 'PING':
                nospoof = args[0][1:] if args[0].startswith(':') else args[0]
                self.send_command(f'PONG :{nospoof}')

            elif 'End of /MOTD command.' in line:
                self.send_command(f'JOIN {self.channel}')

    @pyqtSlot(QTcpSocket.SocketError)
    def on_error_occurred(self, socket_error):
        print(f'Error occurred: {self.socket.errorString()}')

    def send_command(self, command):
        if ' ' in command:
            cmd, args = command.split(' ', 1)
            if cmd in ['JOIN', 'PART']:
                args = args.split(' ', 1)[0]
            self.socket.write(f'{cmd} {args}\r\n'.encode())
        else:
            self.socket.write(f'{command}\r\n'.encode())