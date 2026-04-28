import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ShepherdMessage:
    msg_type: str
    sender_id: str
    recipient_id: str
    sequence_num: int
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    ttl: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_type": self.msg_type,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "timestamp": self.timestamp,
            "sequence_num": self.sequence_num,
            "payload": self.payload,
            "ttl": self.ttl,
        }


class ProtocolSequencer:
    def __init__(self):
        self._sequence_num = 0
        self.pending_acks: Dict[int, ShepherdMessage] = {}

    def next_message(self, msg_type: str, sender_id: str, recipient_id: str, payload: Dict[str, Any], ttl: int = 3) -> ShepherdMessage:
        self._sequence_num += 1
        message = ShepherdMessage(
            msg_type=msg_type,
            sender_id=sender_id,
            recipient_id=recipient_id,
            sequence_num=self._sequence_num,
            payload=payload,
            ttl=ttl,
        )
        if msg_type == "COMMAND":
            self.pending_acks[message.sequence_num] = message
        return message

    def ack(self, sequence_num: int) -> bool:
        return self.pending_acks.pop(sequence_num, None) is not None

    def expired_commands(self, now: float, timeout_s: float = 2.0) -> Dict[int, ShepherdMessage]:
        return {
            sequence_num: message
            for sequence_num, message in self.pending_acks.items()
            if now - message.timestamp > timeout_s
        }
