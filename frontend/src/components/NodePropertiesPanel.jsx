import {
  useEffect,
  useState,
} from 'react'

import './NodePropertiesPanel.css'


function NodePropertiesPanel({
  node,
  device,
  onClose,
  onSave,
  onDelete,
}) {
  const [name, setName] =
    useState('')

  const [vcpu, setVcpu] =
    useState(1)

  const [memoryMb, setMemoryMb] =
    useState(1024)

  const [interfaces, setInterfaces] =
    useState(1)


  const isQemu =
    device?.runtime === 'qemu'


  useEffect(() => {
    if (!node) {
      return
    }

    setName(
      node.name || ''
    )

    setVcpu(
      node.properties?.vcpu ??
      device?.defaults?.vcpu ??
      1
    )

    setMemoryMb(
      node.properties?.memory_mb ??
      device?.defaults?.memory_mb ??
      1024
    )

    setInterfaces(
      node.properties?.interfaces ??
      device?.defaults?.interfaces ??
      device?.interfaces?.default ??
      1
    )
  }, [node, device])


  if (!node) {
    return null
  }


  const handleSubmit = (event) => {
    event.preventDefault()

    const properties = {
      ...node.properties,
    }

    if (isQemu) {
      properties.vcpu =
        Number(vcpu)

      properties.memory_mb =
        Number(memoryMb)

      properties.interfaces =
        Number(interfaces)
    }

    onSave({
      ...node,
      name: name.trim() || node.name,
      properties,
    })
  }


  return (
    <aside className="properties-panel">
      <div className="properties-header">
        <div>
          <span>
            PLANNED DEVICE
          </span>

          <strong>
            {node.name}
          </strong>
        </div>

        <button
          type="button"
          className="properties-close"
          onClick={onClose}
        >
          ×
        </button>
      </div>


      <form
        className="properties-form"
        onSubmit={handleSubmit}
      >
        <div className="properties-template">
          <span>
            Template
          </span>

          <strong>
            {device?.name ||
              node.template_id}
          </strong>

          <small>
            {device?.vendor || 'unknown'}
          </small>
        </div>


        <label>
          Name

          <input
            value={name}
            onChange={(event) =>
              setName(event.target.value)
            }
          />
        </label>


        {isQemu && (
          <>
            <div className="properties-section-title">
              Compute
            </div>

            <label>
              vCPU

              <input
                type="number"
                min="1"
                max="64"
                value={vcpu}
                onChange={(event) =>
                  setVcpu(event.target.value)
                }
              />
            </label>


            <label>
              Memory (MB)

              <input
                type="number"
                min="128"
                step="128"
                value={memoryMb}
                onChange={(event) =>
                  setMemoryMb(
                    event.target.value
                  )
                }
              />
            </label>


            <label>
              Interfaces

              <input
                type="number"
                min="1"
                max="64"
                value={interfaces}
                onChange={(event) =>
                  setInterfaces(
                    event.target.value
                  )
                }
              />
            </label>


            <div className="properties-section-title">
              Image
            </div>

            <div className="image-placeholder">
              <strong>
                No image selected
              </strong>

              <span>
                A biblioteca de imagens
                sera adicionada na proxima
                etapa.
              </span>
            </div>
          </>
        )}


        <div className="properties-actions">
          <button
            type="submit"
            className="properties-save"
          >
            Save changes
          </button>

          <button
            type="button"
            className="properties-delete"
            onClick={() =>
              onDelete(node.id)
            }
          >
            Delete planned device
          </button>
        </div>
      </form>
    </aside>
  )
}


export default NodePropertiesPanel
