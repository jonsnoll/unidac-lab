import {
  useEffect,
  useRef,
  useState,
} from 'react'

import {
  Terminal,
} from '@xterm/xterm'

import {
  FitAddon,
} from '@xterm/addon-fit'

import '@xterm/xterm/css/xterm.css'
import './ConsoleModal.css'


function ConsoleModal({
  nodeId,
  nodeName,
  onClose,
}) {
  const terminalRef =
    useRef(null)

  const [status, setStatus] =
    useState('connecting')


  useEffect(() => {
    const terminal =
      new Terminal({
        cursorBlink: true,
        convertEol: true,
        fontSize: 13,
        scrollback: 3000,
      })


    const fitAddon =
      new FitAddon()


    terminal.loadAddon(
      fitAddon
    )


    terminal.open(
      terminalRef.current
    )


    fitAddon.fit()


    terminal.focus()


    const protocol =
      window.location.protocol ===
      'https:'
        ? 'wss'
        : 'ws'


    const url =
      `${protocol}://` +
      `${window.location.hostname}:8000` +
      `/api/lab/nodes/${
        encodeURIComponent(
          nodeId
        )
      }/console/ws`


    const socket =
      new WebSocket(
        url
      )


    const dataSubscription =
      terminal.onData(
        (data) => {
          if (
            socket.readyState ===
            WebSocket.OPEN
          ) {
            socket.send(
              data
            )
          }
        }
      )


    socket.onopen = () => {
      setStatus('connected')

      terminal.write(
        '\r\n[connected]\r\n'
      )

      socket.send('\r')
    }


    socket.onmessage = (
      event
    ) => {
      terminal.write(
        String(
          event.data
        )
      )
    }


    socket.onerror = () => {
      setStatus('error')

      terminal.write(
        '\r\n[websocket error]\r\n'
      )
    }


    socket.onclose = () => {
      setStatus(
        (current) =>
          current === 'error'
            ? 'error'
            : 'disconnected'
      )

      terminal.write(
        '\r\n[console disconnected]\r\n'
      )
    }


    const handleResize = () => {
      try {
        fitAddon.fit()

      } catch {
        // Modal may be closing.
      }
    }


    window.addEventListener(
      'resize',
      handleResize
    )


    return () => {
      window.removeEventListener(
        'resize',
        handleResize
      )

      dataSubscription.dispose()

      socket.close()

      terminal.dispose()
    }
  }, [
    nodeId,
  ])


  return (
    <div className="console-overlay">
      <div className="console-modal">
        <div className="console-header">
          <div>
            <strong>
              Console
            </strong>

            <span>
              {nodeName}
            </span>
          </div>


          <div className="console-header-right">
            <span
              className={
                `console-status ${status}`
              }
            >
              {status}
            </span>

            <button
              type="button"
              onClick={onClose}
            >
              ×
            </button>
          </div>
        </div>


        <div
          className="console-terminal"
          ref={terminalRef}
        />
      </div>
    </div>
  )
}


export default ConsoleModal
