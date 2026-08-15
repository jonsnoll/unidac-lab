import {
  useEffect,
  useState,
} from 'react'

import './LinkCaptureModal.css'


function errorMessage(data) {
  return (
    data?.detail?.message ||
    data?.message ||
    'Capture operation failed.'
  )
}


function formatBytes(bytes) {
  if (!bytes) {
    return '0 B'
  }

  if (bytes >= 1024 * 1024) {
    return (
      `${(
        bytes /
        (1024 * 1024)
      ).toFixed(1)} MiB`
    )
  }

  if (bytes >= 1024) {
    return (
      `${(
        bytes / 1024
      ).toFixed(1)} KiB`
    )
  }

  return `${bytes} B`
}


function LinkCaptureModal({
  link,
  onClose,
}) {
  const [captureId, setCaptureId] =
    useState(null)

  const [status, setStatus] =
    useState('ready')

  const [sizeBytes, setSizeBytes] =
    useState(0)

  const [runtimeInterface, setRuntimeInterface] =
    useState('')

  const [error, setError] =
    useState('')


  useEffect(() => {
    if (
      !captureId ||
      status !== 'running'
    ) {
      return undefined
    }


    const interval = window.setInterval(
      async () => {
        try {
          const response = await fetch(
            `/api/lab/captures/${
              encodeURIComponent(
                captureId
              )
            }`
          )

          const data =
            await response.json()


          if (!response.ok) {
            return
          }


          setSizeBytes(
            data.result
              ?.size_bytes ||
            0
          )


          if (
            data.result?.status
            !== 'running'
          ) {
            setStatus(
              data.result?.status ||
              'finished'
            )
          }

        } catch {
          // Keep the current state.
        }
      },
      1000,
    )


    return () => {
      window.clearInterval(
        interval
      )
    }
  }, [
    captureId,
    status,
  ])


  async function startCapture() {
    setError('')
    setStatus('starting')


    try {
      const response = await fetch(
        `/api/lab/links/${
          encodeURIComponent(
            link.linkId
          )
        }/capture/start`,
        {
          method: 'POST',
        }
      )

      const data =
        await response.json()


      if (!response.ok) {
        throw new Error(
          errorMessage(data)
        )
      }


      setCaptureId(
        data.capture_id
      )

      setRuntimeInterface(
        data.result
          ?.interface ||
        ''
      )

      setSizeBytes(
        data.result
          ?.size_bytes ||
        0
      )

      setStatus('running')

    } catch (err) {
      setStatus('ready')

      setError(
        err.message
      )
    }
  }


  async function stopCapture() {
    if (!captureId) {
      return
    }


    setError('')
    setStatus('stopping')


    try {
      const response = await fetch(
        `/api/lab/captures/${
          encodeURIComponent(
            captureId
          )
        }/stop`,
        {
          method: 'POST',
        }
      )

      const data =
        await response.json()


      if (!response.ok) {
        throw new Error(
          errorMessage(data)
        )
      }


      setSizeBytes(
        data.result
          ?.size_bytes ||
        0
      )

      setStatus(
        data.result?.status ||
        'finished'
      )

    } catch (err) {
      setStatus('running')

      setError(
        err.message
      )
    }
  }


  function downloadCapture() {
    if (!captureId) {
      return
    }


    window.open(
      `/api/lab/captures/${
        encodeURIComponent(
          captureId
        )
      }/download`,
      '_blank',
    )
  }


  const finished = [
    'stopped',
    'finished',
  ].includes(status)


  return (
    <div className="capture-overlay">
      <div className="capture-modal">
        <div className="capture-header">
          <div>
            <strong>
              Packet Capture
            </strong>

            <span>
              {link.sourceName}
              {' ↔ '}
              {link.targetName}
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
          >
            ×
          </button>
        </div>


        <div className="capture-body">
          <div className="capture-link">
            <div>
              <span>Link</span>

              <strong>
                {link.portLabel || '-'}
              </strong>
            </div>

            <div>
              <span>Status</span>

              <strong
                className={
                  `capture-state ${status}`
                }
              >
                {status.toUpperCase()}
              </strong>
            </div>

            {runtimeInterface && (
              <div>
                <span>
                  Runtime interface
                </span>

                <code>
                  {runtimeInterface}
                </code>
              </div>
            )}

            {captureId && (
              <>
                <div>
                  <span>
                    Capture ID
                  </span>

                  <code>
                    {captureId}
                  </code>
                </div>

                <div>
                  <span>
                    Captured
                  </span>

                  <strong>
                    {
                      formatBytes(
                        sizeBytes
                      )
                    }
                  </strong>
                </div>
              </>
            )}
          </div>


          {error && (
            <div className="capture-error">
              {error}
            </div>
          )}
        </div>


        <div className="capture-footer">
          <button
            type="button"
            className="capture-secondary"
            onClick={onClose}
          >
            Close
          </button>


          {status === 'ready' && (
            <button
              type="button"
              className="capture-primary"
              onClick={startCapture}
            >
              Start Capture
            </button>
          )}


          {status === 'starting' && (
            <button
              type="button"
              className="capture-primary"
              disabled
            >
              Starting...
            </button>
          )}


          {status === 'running' && (
            <button
              type="button"
              className="capture-stop"
              onClick={stopCapture}
            >
              Stop Capture
            </button>
          )}


          {status === 'stopping' && (
            <button
              type="button"
              className="capture-stop"
              disabled
            >
              Stopping...
            </button>
          )}


          {finished && (
            <button
              type="button"
              className="capture-primary"
              onClick={
                downloadCapture
              }
            >
              Download PCAP
            </button>
          )}
        </div>
      </div>
    </div>
  )
}


export default LinkCaptureModal
