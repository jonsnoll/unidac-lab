import { useEffect } from 'react'

import {
  Handle,
  Position,
  useUpdateNodeInternals,
} from '@xyflow/react'

import './PlannedDeviceNode.css'


function PlannedDeviceNode({
  id,
  data,
}) {
  const updateNodeInternals =
    useUpdateNodeInternals()

  const infrastructure =
    data.kind === 'network' ||
    data.kind === 'cloud'


  const interfaceCount =
    Number(
      data.interfaceCount || 1
    )


  useEffect(() => {
    updateNodeInternals(id)
  }, [
    id,
    interfaceCount,
    updateNodeInternals,
  ])


  const ports =
    infrastructure
      ? []
      : Array.from(
          {
            length: interfaceCount,
          },
          (_, index) => ({
            id:
              `${data.interfacePrefix || 'nic'}${index + 1}`,

            label:
              `${data.interfacePrefix || 'nic'}${index + 1}`,
          })
        )


  return (
    <div className="planned-device-node">
      <div className="planned-device-state">
        PLANNED
      </div>

      <strong className="planned-device-name">
        {data.name}
      </strong>

      <span className="planned-device-template">
        {data.templateName}
      </span>


      {infrastructure ? (
        <>
          <Handle
            id="network-left"
            type="source"
            position={Position.Left}
            className="planned-handle"
          />

          <Handle
            id="network-right"
            type="source"
            position={Position.Right}
            className="planned-handle"
          />

          <div className="planned-network-label">
            shared segment
          </div>
        </>
      ) : (
        <div className="planned-port-list">
          {ports.map((port) => (
            <div
              className="planned-port"
              key={port.id}
            >
              <span>
                {port.label}
              </span>

              <Handle
                id={port.id}
                type="source"
                position={Position.Right}
                className="planned-handle planned-port-handle"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


export default PlannedDeviceNode
