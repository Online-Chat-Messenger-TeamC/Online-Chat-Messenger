import socket
import json
import secrets
import datetime
import threading


# rooms_list = {
#     "ルーム名A": {
#         "members": {
#             "トークン1": ("クライアント1のIPアドレス", UDPポート番号)
#             "トークン2": ("クライアント2のIPアドレス", UDPポート番号)
#         },
#         "password": "パスワード(平文)"
#     },
#     "ルーム名B": {
#         "members": {
#             "トークン3": ("クライアント3のIPアドレス", UDPポート番号)
#             "トークン4": ("クライアント4のIPアドレス", UDPポート番号)
#         },
#         "password": "パスワード(平文)"
#     }
# }

# token_list = {
#     "トークン1": {
#         "room_name": "ルーム名A",
#         "user_name": "ユーザー名",
#         "last_access": datetime.datetime.now(), # 最終メッセージ送信時刻
#         "is_host": True  # ホスト
#     },
#     "トークン2": {
#         "room_name": "ルーム名A",
#         "user_name": "ユーザー名",
#         "last_access": datetime.datetime.now(), # 最終メッセージ送信時刻
#         "is_host": False # ホストではない
#     },
#     ...
# }

# ルーム情報とトークン情報のグローバル変数
rooms_list = {}
token_list = {}

# 共有リストアクセス用のロック
list_lock = threading.Lock()

# UDPクライアントのタイムアウト時間
UDP_CLIENT_TIME_OUT = 10

# 最終メッセージ送信時間を定期的に確認
LAST_MESSAGE_TIME = 5

# システムメッセージ
SYSTEM_MESSAGE = "SYSTEM_MESSAGE_TIME_OUT"
SYSTEM_HOST_MESSAGE = "SYSTEM_HOST_MESSAGE_TIME_OUT"
# TCPサーバー


class TCPServer:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.address, self.port))
        self.sock.listen()

        self.rooms_list = rooms_list
        self.token_list = token_list

    def recieve_request(self):
        print(f"TCPサーバー起動 {self.address}:{self.port}")
        while True:
            client_socket, client_address = self.sock.accept()
            print(f"\n{client_address} から接続")

            try:
                header_data = client_socket.recv(32)
                if not header_data or len(header_data) < 32:
                    print("無効なヘッダー")
                    client_socket.close()
                    continue

                room_name_len = int.from_bytes(header_data[0:1], "big")
                operation = int.from_bytes(header_data[1:2], "big")
                state = int.from_bytes(header_data[2:3], "big")
                operation_payload_len = int.from_bytes(header_data[3:32], "big")

                room_name_bytes = client_socket.recv(room_name_len)
                room_name = room_name_bytes.decode("utf-8")

                operation_payload_bytes = client_socket.recv(operation_payload_len)
                operation_payload = json.loads(operation_payload_bytes.decode("utf-8"))

                response = {}

                user_name = operation_payload.get("user_name")
                password = operation_payload.get("password", "")
                udp_port = operation_payload.get("udp_port", None)

                with list_lock:
                    if operation == 1:
                        if room_name in self.rooms_list:
                            response = {
                                "message": f"ルーム名 '{room_name}' は存在します。",
                                "operation": operation,
                                "state": 1,
                                "user_name": user_name,
                            }
                        else:
                            new_token = secrets.token_urlsafe(32)
                            now = datetime.datetime.now()

                            self.rooms_list[room_name] = {
                                "members": {new_token: (client_address[0], udp_port)},
                                "password": password,
                            }

                            self.token_list[new_token] = {
                                "room_name": room_name,
                                "user_name": user_name,
                                "last_access": now,
                                "is_host": True,
                            }

                            response = {
                                "message": f"新しいルーム '{room_name}' を作成しました。",
                                "operation": operation,
                                "state": 2,
                                "user_name": user_name,
                                "token": new_token,
                            }

                    elif operation == 2:
                        if room_name not in self.rooms_list:
                            response = {
                                "message": f"ルーム名 '{room_name}' は存在しません。",
                                "operation": operation,
                                "state": 1,
                                "user_name": user_name,
                            }
                        else:
                            room_info = self.rooms_list[room_name]

                            if room_info.get("password") != password:
                                response = {
                                    "message": "パスワードが違います。",
                                    "operation": operation,
                                    "state": 1,
                                    "user_name": user_name,
                                }
                            else:
                                new_token = secrets.token_urlsafe(32)
                                now = datetime.datetime.now()

                                room_info["members"][new_token] = (
                                    client_address[0],
                                    udp_port,
                                )

                                self.token_list[new_token] = {
                                    "room_name": room_name,
                                    "user_name": user_name,
                                    "last_access": now,
                                    "is_host": False,
                                }

                                response = {
                                    "message": f"ルーム '{room_name}' に参加しました。",
                                    "operation": operation,
                                    "state": 2,
                                    "user_name": user_name,
                                    "token": new_token,
                                }

                print("\n---------- リクエスト元のTCPクライアント情報 ----------")
                print(f"接続元: ('{client_address[0]}', {client_address[1]})")
                print(
                    f"操作種類: {'ルーム作成' if operation == 1 else 'ルーム参加' if operation == 2 else '不明'}"
                )
                print(f"ルーム名: {room_name}")
                print(f"ユーザー名: {user_name}")
                print(f"パスワード: {password}")
                print(
                    f"ホスト: {'True' if operation == 1 else 'False' if operation == 2 else '不明'}"
                )
                print(f"状態コード: " + str(response.get("state")))
                print(f"メッセージ: " + str(response.get("message")))
                print(f"トークン: " + str(response.get("token")))
                print("------------------------------------------------------")

                response_data = json.dumps(response).encode("utf-8")
                client_socket.sendall(response_data)

            except Exception as err:
                print(f"エラー：{err}")

            finally:
                client_socket.close()

    def send_response(self, data):
        self.sock.sendall(data)

    def close(self):
        self.sock.close()


# UDPサーバー


class UDPServer:
    def __init__(self, address, port):
        self.room_list = rooms_list
        self.token_list = token_list

        self.address = address
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.address, self.port))

    def start(self):
        print(f"UDPサーバー起動 {self.address}:{self.port}")
        self.cleanup_thread = threading.Thread(
            target=self.cleanup_inactive_clients, daemon=True
        )
        self.cleanup_thread.start()

        while True:
            data, addr = self.sock.recvfrom(4096)
            ip, udp_port = addr
            print(f"{addr}: {data} を受信(UDP)")
            print(f"受信データ: {data} (長さ: {len(data)})")

            try:
                if not data or len(data) < 2:
                    print("パケットが短すぎます。")
                    continue

                room_name_len = data[0]
                user_name_len = data[1]
                token_len = data[2]

                min_len = 2 + room_name_len + token_len
                if len(data) < min_len:
                    print("パケットが不完全です。")
                    continue

                room_name_bytes = data[3 : 3 + room_name_len]
                user_name_bytes = data[
                    3 + room_name_len : 3 + room_name_len + user_name_len
                ]
                token_bytes = data[
                    3
                    + room_name_len
                    + user_name_len : 3
                    + room_name_len
                    + user_name_len
                    + token_len
                ]
                message_bytes = data[3 + room_name_len + user_name_len + token_len :]

                room_name = room_name_bytes.decode("utf-8")
                user_name = user_name_bytes.decode("utf-8")
                token = token_bytes.decode("utf-8")
                message = message_bytes.decode("utf-8")

                with list_lock:
                    if token not in self.token_list:
                        print("無効なトークンのメッセージを受信しました。")
                        continue

                    # 初回メッセージ受信時にクライアントのUDPポートを登録
                    if self.room_list[room_name]["members"][token] == (ip, None):
                        self.room_list[room_name]["members"][token] = (ip, udp_port)

                    # メッセージ受信時にlast_accessを更新
                    self.token_list[token]["last_access"] = datetime.datetime.now()

                    # メッセージを同ルームの他クライアントに送信
                    for member_token, (member_ip, member_udp_port) in self.room_list[
                        room_name
                    ]["members"].items():
                        if member_token != token:
                            self.sock.sendto(data, (member_ip, member_udp_port))

                    print(f"{user_name}: {message}")
                    print(
                        f"{room_name} にメッセージを転送しました: {user_name}: {message}"
                    )

            except Exception as e:
                print(f"UDP受信エラー: {e}")
                self.sock.sendto(f"エラー: {str(e)}".encode("utf-8"), addr)

    def send_system_message(self, room_name, token, user_name, message, address):
        try:
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

            self.sock.sendto(packet, address)

        except Exception as e:
            print(f"サーバーメッセージ送信エラー: {address}: {e}")

    def cleanup_inactive_clients(self):
        while True:
            with list_lock:
                now = datetime.datetime.now()
                tokens_to_remove = []  # 非アクティブな client を格納
                for token, info in list(self.token_list.items()):
                    last_access = info.get("last_access")
                    if (last_access) and (
                        now - last_access
                    ).total_seconds() > UDP_CLIENT_TIME_OUT:
                        tokens_to_remove.append(token)

                # 削除する client を1人ずつ処理
                for token in tokens_to_remove:
                    if token in self.token_list:
                        client_info = self.token_list[token]
                        room_name = client_info["room_name"]
                        user_name = client_info["user_name"]
                        is_host = client_info["is_host"]
                        print(
                            f"クライアント '{user_name}' (token: {token}) をルーム '{room_name}' から削除します（タイムアウト {UDP_CLIENT_TIME_OUT}秒)。"
                        )

                        # room_list から特定のクライアントのトークンを削除
                        if (
                            room_name in self.room_list
                            and token in self.room_list[room_name]["members"]
                        ):
                            # タイムアウトするクライアントへ送信
                            self.send_system_message(
                                room_name,
                                token,
                                user_name,
                                SYSTEM_MESSAGE,
                                self.room_list[room_name]["members"][token],
                            )
                            del self.room_list[room_name]["members"][token]

                            if is_host:
                                print(
                                    f"ホストが退出したため、ルーム '{room_name}' を削除します。"
                                )
                                members_in_room = list(
                                    self.room_list[room_name]["members"].keys()
                                )
                                # ホストが退出したルームのメンバーをすべて削除
                                for member_token in members_in_room:
                                    if member_token in self.token_list:
                                        self.send_system_message(
                                            room_name,
                                            member_token,
                                            user_name,
                                            SYSTEM_HOST_MESSAGE,
                                            self.room_list[room_name]["members"][
                                                member_token
                                            ],
                                        )
                                        del self.token_list[member_token]

                                del self.room_list[room_name]

                    del self.token_list[token]

            threading.Event().wait(LAST_MESSAGE_TIME)

    def close(self):
        self.sock.close()


if __name__ == "__main__":

    # TCPサーバーの実行
    tcp_server = TCPServer("127.0.0.1", 8080)
    tcp_thread = threading.Thread(target=tcp_server.recieve_request)
    tcp_thread.start()

    # UDPサーバーの実行
    udp_server = UDPServer("127.0.0.1", 8080)
    udp_thread = threading.Thread(target=udp_server.start)
    udp_thread.start()

    tcp_thread.join()
    udp_thread.join()
