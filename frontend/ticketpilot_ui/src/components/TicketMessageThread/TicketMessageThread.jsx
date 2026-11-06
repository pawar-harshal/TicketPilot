import { useEffect, useRef } from "react";
import { Typography } from "antd";
import { formatDateTime } from "../../utils/helper";

import "./TicketMessageThread.css";

const SENDER_LABEL = {
  customer: "You",
  agent: "TicketPilot Agent",
  system: "QuickCrave",
};

/**
 * Renders a ticket's TicketMessage history as real chat bubbles --
 * customer on the right (brand orange), agent on the left (white card),
 * system notices centered as a small pill. Raw tool-call JSON
 * (Ticket.T_InvestigationTrail) is intentionally NOT shown here --
 * customers only ever see the human-readable conversation.
 */
function TicketMessageThread({ messages = [], typing = false }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, typing]);

  if (messages.length === 0) {
    return (
      <div className="chat-thread chat-thread--empty">
        <Typography.Text type="secondary">No messages yet.</Typography.Text>
      </div>
    );
  }

  return (
    <div className="chat-thread">
      {messages.map((msg, idx) => {
        if (msg.sender === "system") {
          return (
            <div className="chat-system-row" key={idx}>
              <span className="chat-system-pill">{msg.message}</span>
            </div>
          );
        }

        const isCustomer = msg.sender === "customer";
        return (
          <div
            key={idx}
            className={`chat-row ${isCustomer ? "chat-row--customer" : "chat-row--agent"}`}
          >
            <div className={`chat-bubble ${isCustomer ? "chat-bubble--customer" : "chat-bubble--agent"}`}>
              {!isCustomer && <div className="chat-bubble__sender">{SENDER_LABEL[msg.sender] || "Agent"}</div>}
              <div className="chat-bubble__text">{msg.message}</div>
              <div className="chat-bubble__time">
                {formatDateTime(msg.created_date)}
                {isCustomer && <span className="chat-bubble__ticks">✓✓</span>}
              </div>
            </div>
          </div>
        );
      })}

      {typing && (
        <div className="chat-row chat-row--agent">
          <div className="chat-bubble chat-bubble--agent chat-bubble--typing">
            <span className="chat-typing-label">Looking into your order…</span>
            <span className="chat-typing-dot" />
            <span className="chat-typing-dot" />
            <span className="chat-typing-dot" />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}

export default TicketMessageThread;
