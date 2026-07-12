extends Node

## UDP client for talking to the Python backend.
## Sends player actions, receives sim-state ticks.

const HOST: String = "127.0.0.1"
const PORT: int = 9999

signal sim_state_received(state: Dictionary)

var _socket: PacketPeerUDP
var _last_state: Dictionary = {}

func _ready() -> void:
	_socket = PacketPeerUDP.new()
	var err: int = _socket.set_dest_address(HOST, PORT)
	if err != OK:
		push_error("Bridge: cannot set destination %s:%d (err %d)" % [HOST, PORT, err])

func send_action(action: String, payload: Dictionary = {}) -> void:
	if _socket == null:
		return
	var msg: Dictionary = {"action": action, "payload": payload}
	_socket.put_packet(JSON.stringify(msg).to_utf8_buffer())

func _process(_delta: float) -> void:
	if _socket == null:
		return
	# Receive is non-blocking in Godot 4 UDP peer.
	while _socket.get_available_packet_count() > 0:
		var pkt: PackedByteArray = _socket.get_packet()
		var raw: String = pkt.get_string_from_utf8()
		var parsed: Variant = JSON.parse_string(raw)
		if parsed is Dictionary and parsed.get("type") == "state":
			_last_state = parsed
			sim_state_received.emit(parsed)
