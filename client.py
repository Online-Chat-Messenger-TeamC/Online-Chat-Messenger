import socket
import json
import threading
import os

# TCPデータ構造:
# operation = "操作コード(1 or 2)"
# state = "状態コード(0 ~ 2)"
# room_name = "ルーム名"
# operation_payload = {
#     user_name = "ユーザー名"
#     token = "トークン"
#     password = "パスワード(平文)"
# }

# UDPデータ構造:
# header = (
#     # RoomNameSize + UserNameSize + TokenSize
#     len(room_name_bytes).to_bytes(1, "big") +
#     len(user_name_bytes).to_bytes(1, "big") +
#     len(token_bytes).to_bytes(1, "big")
# )
# body = (
#     # RoomName + UserName + Token + Message
#     room_name_bytes +
#     user_name_bytes +
#     token_bytes +
#     message_bytes
# )


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

    def make_tcp_request(
        self, room_name, operation, state, user_name, password, token=""
    ):
        # オペレーションペイロードの作成
        operation_payload = {
            "user_name": user_name,
            "token": token,
            "password": password,
        }

        room_name_bytes = room_name.encode("utf-8")
        operation_payload_bytes = json.dumps(operation_payload).encode("utf-8")

        operation = int(operation)
        state = int(state)

        # ヘッダーの作成
        header = (
            len(room_name_bytes).to_bytes(1, "big")
            + operation.to_bytes(1, "big")
            + state.to_bytes(1, "big")
            + len(operation_payload_bytes).to_bytes(29, "big")
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

    def send_message(self, room_name, user_name, token, message):
        room_name_bytes = room_name.encode("utf-8")
        token_bytes = token.encode("utf-8")
        user_name_bytes = user_name.encode("utf-8")
        message_bytes = message.encode("utf-8")

        header = (
            len(room_name_bytes).to_bytes(1, "big")
            + len(user_name_bytes).to_bytes(1, "big")
            + len(token_bytes).to_bytes(1, "big")
        )

        body = room_name_bytes + user_name_bytes + token_bytes + message_bytes

        packet = header + body

        self.sock.sendto(packet, (self.address, self.port))

    def receive_messages(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(4096)
                if len(data) < 3:
                    continue

                room_name_len = data[0]
                user_name_len = data[1]
                token_len = data[2]
                min_len = 3 + room_name_len + user_name_len + token_len

                if len(data) < min_len:
                    continue

                room_name = data[3 : 3 + room_name_len].decode("utf-8")
                user_name = data[
                    3 + room_name_len : 3 + room_name_len + user_name_len
                ].decode("utf-8")
                message = data[min_len:].decode("utf-8")

                # タイムアウトするクライアントと自身が一致する場合
                if message == "SYSTEM_MESSAGE_TIME_OUT" and user_name == self.user_name:
                    print("\033[2K\r", end="")
                    print("---------------------------------------------------------")
                    print(
                        f"{user_name} が ルーム '{room_name}' からタイムアウトしました。"
                    )
                    print(f"プログラムを終了します。")
                    self.sock.close()
                    os._exit(0)

                elif (
                    # タイムアウトするクライアントと自身が一致しない場合
                    message == "SYSTEM_MESSAGE_TIME_OUT"
                    and user_name != self.user_name
                ):
                    print("\033[2K\r", end="")
                    print("---------------------------------------------------------")
                    print(
                        f"{user_name} が ルーム '{room_name}' からタイムアウトしました。"
                    )

                # ホストであるクライアントが退出する場合
                elif message == "SYSTEM_HOST_MESSAGE_TIME_OUT":
                    print("\033[2K\r", end="")
                    print("------------------------------------------------------")
                    print(
                        f"ホストが退出したため ルーム '{room_name}' から退出しました。"
                    )
                    print(f"プログラムを終了します。")
                    self.sock.close()
                    os._exit(0)

                # 通常のメッセージが送信された場合
                elif message:
                    print("\033[2K\r", end="")
                    print(f"{user_name}: {message}")
                    print(f"{self.user_name} :> ", end="", flush=True)

            except Exception as e:
                print(f"\n[受信エラー]: {e}")

    def input_loop(self):
        while True:
            try:
                message = input(f"{self.user_name} :> ")
                print("\033[1A\033[2K", end="")
                print(f"{self.user_name} : {message}")
                self.send_message(self.room_name, self.user_name, self.token, message)
            except KeyboardInterrupt:
                print("\n終了します。")
                break

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

        data = tcp_client.make_tcp_request(
            room_name, operation, "0", user_name, password
        )

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

    udp_client.user_name = user_name
    udp_client.room_name = room_name
    udp_client.token = token

    print(f"{user_name} がルーム '{room_name}' に参加しました。")

    recv_thread = threading.Thread(target=udp_client.receive_messages, daemon=True)
    recv_thread.start()

    udp_client.send_message(
        room_name, user_name, token, f"{user_name} がルームに参加しました"
    )

    udp_client.input_loop()

    udp_client.close()
