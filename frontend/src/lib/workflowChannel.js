const CHANNEL_NAME = 'clever-workflow-network'

let channel = null

function getChannel() {
  if (typeof window === 'undefined' || typeof BroadcastChannel === 'undefined') {
    return null
  }
  if (!channel) {
    channel = new BroadcastChannel(CHANNEL_NAME)
  }
  return channel
}

export function publishWorkflowEvent(event) {
  const workflowChannel = getChannel()
  if (!workflowChannel) return

  workflowChannel.postMessage({
    ...event,
    emittedAt: Date.now(),
  })
}

export function subscribeWorkflowEvents(handler) {
  const workflowChannel = getChannel()
  if (!workflowChannel) {
    return () => {}
  }

  const listener = (message) => {
    handler(message.data)
  }

  workflowChannel.addEventListener('message', listener)
  return () => workflowChannel.removeEventListener('message', listener)
}
