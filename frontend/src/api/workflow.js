import client from './client'

export const fetchWorkflowMonitorSnapshot = () =>
  client.get('/dashboard/workflow-monitor/')
