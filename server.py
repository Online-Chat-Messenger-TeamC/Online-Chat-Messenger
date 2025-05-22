import socket
import json
import secrets
import datetime
import threading

# TCPデータ構造:
# operation = "操作コード(1 or 2)"
# state = "状態コード(0 ~ 2)"
# room_name = "ルーム名"
# operation_payload = {
#     user_name = "ユーザー名"
#     token = "トークン"
#     password = "パスワード(平文)"
#     status = "ステータスコード"
# }

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

# TCPサーバー

class TCPServer:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.address, self.port))
        self.sock.listen()

    def recieve_request(self):
        print(f"TCPサーバー起動 {self.address}:{self.port}")
        while True:
            client_socket, client_address = self.sock.accept()
            print(f"{client_address} から接続")

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

                print(f"データ受信: room_name={room_name}, operation={operation}, state={state}, payload={operation_payload}")

                response = {
                    "message": f"{room_name} に対する操作を受け付けました。",
                    "operation": operation,
                    "state": state,
                    "user_name": operation_payload.get("user_name")
                }

                response_data = json.dumps(response).encode("utf-8")
                client_socket.sendall(response_data)

            except Exception as err:
                print(f"エラー：{err}")

            finally:
                client_socket.close()

            # 以下ヘッダー・ボディのデコードのテスト

            # ヘッダーのデコード
            # room_name_len = int.from_bytes(header_data[0:1], "big")
            # operation = int.from_bytes(header_data[1:2], "big")
            # state = int.from_bytes(header_data[2:3], "big")
            # operation_payload_len = int.from_bytes(header_data[3:32], "big")

            # print(f"room_name_len: {room_name_len}")
            # print(f"operation: {operation}")
            # print(f"state: {state}")
            # print(f"operation_payload_len: {operation_payload_len}")

            # room_name_bytes = client_socket.recv(room_name_len)

            # ルームネームのデコード
            # room_name = room_name_bytes.decode("utf-8")
            # print(f"room_name: {room_name}")

            # オペレーションペイロードのデコード
            # operation_payload_bytes = client_socket.recv(operation_payload_len)
            # operation_payload = json.loads(operation_payload_bytes.decode("utf-8"))
            # print(f"operation_payload: {operation_payload}")


    def send_response(self, data):
        self.sock.sendall(data)

    def close(self):
        self.sock.close()


# UDPサーバー

class UDPServer:
    def __init__(self, address, port):
        self.room_list = {}
        self.token_list = {}

        self.address = address
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.address, self.port))

    def start(self):
        print(f"UDPサーバー起動 {self.address}:{self.port}")
        while True:
            data, addr = self.sock.recvfrom(1024)
            print(f"{addr}: {data} を受信(UDP)")
            self.sock.sendto(b"UDPServerHello, client!", addr)

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
