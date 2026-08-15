import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import './NodePropertiesPanel.css'


function formatBytes(bytes) {
  if (!bytes) {
    return '-'
  }

  const gib = bytes / (1024 ** 3)
  const mib = bytes / (1024 ** 2)

  if (gib >= 1) {
    return `${gib.toFixed(1)} GiB`
  }

  return `${mib.toFixed(0)} MiB`
}


function NodePropertiesPanel({
  node,
  device,
  images,
  runtimeId,
  runtimeState,
  onLifecycle,
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

  const [imageId, setImageId] =
    useState('')


  const [
    lifecycleAction,
    setLifecycleAction,
  ] = useState('')


  const [
    lifecycleError,
    setLifecycleError,
  ] = useState('')


  const isQemu =
    device?.runtime === 'qemu'


  const compatibleImages =
    useMemo(
      () =>
        images.filter(
          (image) =>
            image.available &&
            (
              image.compatible_templates ||
              []
            ).includes(
              node?.template_id
            )
        ),
      [
        images,
        node?.template_id,
      ]
    )


  const selectedImage =
    compatibleImages.find(
      (image) =>
        image.id === imageId
    )


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

    setImageId(
      node.properties?.image_id ??
      ''
    )
  }, [node, device])


  if (!node) {
    return null
  }


  const runtimeRunning =
    runtimeState === 'running'


  const runtimeAvailable =
    Boolean(
      runtimeId &&
      runtimeState
    )


  const handleLifecycle =
    async (operation) => {
      if (
        !onLifecycle ||
        lifecycleAction
      ) {
        return
      }


      setLifecycleError('')
      setLifecycleAction(
        operation
      )


      try {
        await onLifecycle(
          node.id,
          operation,
        )

      } catch (error) {
        setLifecycleError(
          error.message ||
          'Erro executando lifecycle.'
        )

      } finally {
        setLifecycleAction('')
      }
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

      if (imageId) {
        properties.image_id =
          imageId
      } else {
        delete properties.image_id
      }
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
            {
              runtimeAvailable
                ? runtimeState.toUpperCase()
                : 'PLANNED DEVICE'
            }
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


            {compatibleImages.length > 0 ? (
              <>
                <label>
                  Image

                  <select
                    value={imageId}
                    onChange={(event) =>
                      setImageId(
                        event.target.value
                      )
                    }
                  >
                    <option value="">
                      Select image...
                    </option>

                    {compatibleImages.map(
                      (image) => (
                        <option
                          key={image.id}
                          value={image.id}
                        >
                          {image.name}
                        </option>
                      )
                    )}
                  </select>
                </label>


                {selectedImage && (
                  <div className="image-details">
                    <div>
                      <span>
                        Status
                      </span>

                      <strong>
                        Available
                      </strong>
                    </div>

                    <div>
                      <span>
                        Format
                      </span>

                      <strong>
                        {selectedImage.format}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Virtual size
                      </span>

                      <strong>
                        {formatBytes(
                          selectedImage
                            .image_info
                            ?.virtual_size_bytes
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Stored size
                      </span>

                      <strong>
                        {formatBytes(
                          selectedImage
                            .file_size_bytes
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Deployment
                      </span>

                      <strong>
                        {
                          selectedImage
                            .deployment
                        }
                      </strong>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="image-placeholder">
                <strong>
                  No compatible images
                </strong>

                <span>
                  Importe uma imagem
                  compatível com este
                  template.
                </span>
              </div>
            )}
          </>
        )}


        {isQemu && runtimeId && (
          <>
            <div className="properties-section-title">
              Runtime
            </div>


            <div className="runtime-card">
              <div>
                <span>
                  State
                </span>

                <strong
                  className={
                    runtimeRunning
                      ? 'runtime-state running'
                      : 'runtime-state stopped'
                  }
                >
                  {
                    runtimeState
                      ?.toUpperCase() ||
                    'UNKNOWN'
                  }
                </strong>
              </div>


              <div>
                <span>
                  Domain
                </span>

                <code>
                  {runtimeId.replace(
                    /^vm:/,
                    ''
                  )}
                </code>
              </div>


              {lifecycleError && (
                <div className="runtime-error">
                  {lifecycleError}
                </div>
              )}


              <div className="runtime-actions">
                {runtimeRunning ? (
                  <>
                    <button
                      type="button"
                      className="runtime-restart"
                      disabled={
                        Boolean(
                          lifecycleAction
                        )
                      }
                      onClick={() =>
                        handleLifecycle(
                          'restart'
                        )
                      }
                    >
                      {
                        lifecycleAction ===
                        'restart'
                          ? 'Restarting...'
                          : 'Restart'
                      }
                    </button>


                    <button
                      type="button"
                      className="runtime-stop"
                      disabled={
                        Boolean(
                          lifecycleAction
                        )
                      }
                      onClick={() =>
                        handleLifecycle(
                          'shutdown'
                        )
                      }
                    >
                      {
                        lifecycleAction ===
                        'shutdown'
                          ? 'Stopping...'
                          : 'Stop'
                      }
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    className="runtime-start"
                    disabled={
                      Boolean(
                        lifecycleAction
                      )
                    }
                    onClick={() =>
                      handleLifecycle(
                        'start'
                      )
                    }
                  >
                    {
                      lifecycleAction ===
                      'start'
                        ? 'Starting...'
                        : 'Start'
                    }
                  </button>
                )}
              </div>


              {
                runtimeState ===
                'shutoff' && (
                  <div className="runtime-remove">
                    <button
                      type="button"
                      disabled={
                        Boolean(
                          lifecycleAction
                        )
                      }
                      onClick={async () => {
                        const confirmed =
                          window.confirm(
                            'Remove only the runtime VM?\n\n' +
                            'The QCOW2 overlay and planned device ' +
                            'will be preserved.'
                          )


                        if (!confirmed) {
                          return
                        }


                        await handleLifecycle(
                          'remove-runtime'
                        )
                      }}
                    >
                      {
                        lifecycleAction ===
                        'remove-runtime'
                          ? 'Removing runtime...'
                          : 'Remove runtime'
                      }
                    </button>

                    <small>
                      Overlay disk will be preserved.
                    </small>
                  </div>
                )
              }
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
