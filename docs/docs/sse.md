


On the client,

[EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) is a simple way to implement real-time updates in web applications, such as live feeds, notifications, or chat systems. It's a unidirectional communication channel from the server to the client, making it more efficient than bidirectional protocols like WebSockets for certain use cases

EventSource is a web API that allows you to establish a persistent connection with a server and receive server-sent events (SSE) in real-time. Here's how it works:
The client creates a new EventSource instance by passing the URL of the server that will send the events:
js
const eventSource = new EventSource(sseUrl);

The server keeps the connection open and sends data to the client whenever there's new information available. The data is sent in the format of text/event-stream, which consists of one or more lines separated by a double newline.
On the client-side, the EventSource object listens for different types of events and allows you to handle them accordingly. The main events are:
open: Fired when the connection is established.
message: Fired when a message is received from the server. This is the default event if no event type is specified by the server.
error: Fired when an error occurs while receiving an event.

You can listen to these events using the addEventListener method or by setting the corresponding properties (onopen, onmessage, onerror)