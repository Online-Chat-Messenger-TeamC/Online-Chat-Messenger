import socket
import json


# ユーザー名入力で空白を受け付けない
def get_empty_input(prompt):
    while True:
        user_input = input(prompt).strip()
        if user_input:
            return user_input
        else:
            print("入力が無効です。もう一度入力してください。\n")


# TCPクライアント

class TCPClient:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def input_user_name_and_operation(self):
        while True:
            user_name = get_empty_input("ユーザー名を入力してください: ").strip()
            if not user_name:
                continue
            break

        print("1: ルームを作成")
        print("2: ルームに参加")

        while True:
            operation = input("1 または 2 を選択してください: ")
            if not operation == "1" and not operation == "2":
                continue
            break

        return user_name, operation


    def input_room_name_and_password(self, operation):
        while True:
            if operation == "1":
                room_name = get_empty_input("作成するルームの名前を入力してください: ")
                if not room_name:
                    continue
                password = input("パスワードを設定してください: ").strip()
                break

            elif operation == "2":
                room_name = get_empty_input("参加するルームの名前を入力してください: ")
                if not room_name:
                    continue
                password = input("パスワードを入力してください: ").strip()
                break

        return room_name, password


    def make_tcp_request(self, room_name, operation, state, user_name, password, token=""):
        # オペレーションペイロードの作成
        operation_payload = {
            "user_name": user_name,
            "token": token,
            "password": password
        }

        room_name_bytes = room_name.encode("utf-8")
        operation_payload_bytes = json.dumps(operation_payload).encode("utf-8")

        operation = int(operation)
        state = int(state)

        # ヘッダーの作成
        header = (
            len(room_name_bytes).to_bytes(1, "big") +
            operation.to_bytes(1, "big") +
            state.to_bytes(1, "big") +
            len(operation_payload_bytes).to_bytes(29, "big")
        )

        # ヘッダー + ボディ（ルームネームバイト + オペレーションペイロードバイト）
        return header + room_name_bytes + operation_payload_bytes

    def send_request(self, data):
        self.sock.sendall(data)


    def receive_response(self):
        return self.sock.recv(1024)


    def close(self):
        self.sock.close()

# UDPクライアント

class UDPClient:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_message(self, room_name, token, message):
        room_name_bytes = room_name.encode("utf-8")
        token_bytes = token.encode("utf-8")
        message_bytes = message.encode("utf-8")
        
        header = (
            len(room_name_bytes).to_bytes(1, "big") +
            len(token_bytes).to_bytes(1, "big")
        )
        
        body = (
            room_name_bytes +
            token_bytes +
            message_bytes
        )
        
        packet = header + body
        
        self.sock.sendto(packet, (self.address, self.port))

    def receive_message(self):
        return self.sock.recvfrom(1024)

    def close(self):
        self.sock.close()


if __name__ == "__main__":

    # TCPクライアントの実行
    while True:
        tcp_client = TCPClient("127.0.0.1", 8080)

        user_name, operation = tcp_client.input_user_name_and_operation()

        # ユーザー名, 操作コード入力後にTCPサーバーと接続
        tcp_client.sock.connect((tcp_client.address, tcp_client.port))

        room_name, password = tcp_client.input_room_name_and_password(operation)

        data = tcp_client.make_tcp_request(room_name, operation, "0", user_name, password)

        tcp_client.send_request(data)

        response_data = tcp_client.receive_response().decode("utf-8")
        response = json.loads(response_data)
        token = response.get("token")

        try:
            if response.get("state") == 2:
                print(response.get("message"))
                print("-------------------------------------------")
                break

            # ルーム作成を試みたが失敗した場合
            elif response.get("state") == 1 and response.get("operation") == 1:
                print(response.get("message"))
                print("最初からやり直してください")
                print("-------------------------------------------")
                continue

            # ルーム参加を試みたが失敗した場合
            elif response.get("state") == 1 and response.get("operation") == 2:
                print(response.get("message"))
                print("最初からやり直してください")
                print("-------------------------------------------")
                continue

        except json.JSONDecodeError:
            print("サーバーからの応答が不正です。内容:", response_data)
            continue

    tcp_client.close()

    # UDPクライアントの実行
    udp_client = UDPClient("127.0.0.1", 8080)
    print(f"{user_name} がルーム '{room_name}' に参加しました。")
    
    while True:
        message = input(f"{user_name}> ")
        udp_client.send_message(room_name, token, message)
