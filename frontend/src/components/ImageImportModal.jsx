import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import './ImageImportModal.css'


function slugify(value) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}


function ImageImportModal({
  devices,
  onClose,
  onImported,
}) {
  const importableDevices =
    useMemo(
      () =>
        devices.filter(
          (device) =>
            device.image_required
        ),
      [devices]
    )


  const [
    templateId,
    setTemplateId,
  ] = useState('')

  const [name, setName] =
    useState('')

  const [version, setVersion] =
    useState('unknown')

  const [
    imageFormat,
    setImageFormat,
  ] = useState('')

  const [file, setFile] =
    useState(null)

  const [status, setStatus] =
    useState('')

  const [error, setError] =
    useState('')


  const selectedDevice =
    importableDevices.find(
      (device) =>
        device.id === templateId
    )


  const allowedFormats =
    useMemo(
      () =>
        selectedDevice
          ?.image_types || [],
      [selectedDevice]
    )


  const vendor =
    selectedDevice?.vendor || ''


  const generatedId =
    name.trim() && vendor
      ? (
          `${slugify(vendor)}-` +
          `${slugify(name)}`
        ).slice(0, 63)
      : ''


  useEffect(() => {
    if (
      !templateId &&
      importableDevices.length
    ) {
      setTemplateId(
        importableDevices[0].id
      )
    }
  }, [
    templateId,
    importableDevices,
  ])


  useEffect(() => {
    if (
      !allowedFormats.includes(
        imageFormat
      )
    ) {
      setImageFormat(
        allowedFormats[0] || ''
      )
    }
  }, [
    allowedFormats,
    imageFormat,
  ])


  const handleFileChange =
    (event) => {
      const selectedFile =
        event.target.files?.[0]

      setFile(
        selectedFile || null
      )

      setError('')


      if (!selectedFile) {
        return
      }


      const parts =
        selectedFile.name.split('.')

      const extension =
        parts.length > 1
          ? parts.pop().toLowerCase()
          : ''


      if (
        allowedFormats.includes(
          extension
        )
      ) {
        setImageFormat(
          extension
        )
      }
    }


  const handleSubmit =
    async (event) => {
      event.preventDefault()

      setError('')


      if (!selectedDevice) {
        setError(
          'Selecione um template.'
        )

        return
      }


      if (!name.trim()) {
        setError(
          'Informe o nome da imagem.'
        )

        return
      }


      if (!generatedId) {
        setError(
          'Nao foi possivel gerar o ID.'
        )

        return
      }


      if (!imageFormat) {
        setError(
          'Selecione o formato.'
        )

        return
      }


      if (!file) {
        setError(
          'Selecione um arquivo.'
        )

        return
      }


      const formData =
        new FormData()

      formData.append(
        'image_id',
        generatedId
      )

      formData.append(
        'name',
        name.trim()
      )

      formData.append(
        'vendor',
        vendor
      )

      formData.append(
        'version',
        version.trim() ||
          'unknown'
      )

      formData.append(
        'template_id',
        templateId
      )

      formData.append(
        'image_format',
        imageFormat
      )

      formData.append(
        'file',
        file
      )


      setStatus(
        'Importando imagem...'
      )


      try {
        const response =
          await fetch(
            '/api/images/import',
            {
              method: 'POST',
              body: formData,
            }
          )


        const data =
          await response.json()


        if (!response.ok) {
          const detail =
            typeof data.detail ===
            'string'
              ? data.detail
              : JSON.stringify(
                  data.detail
                )

          throw new Error(
            detail ||
            `HTTP ${response.status}`
          )
        }


        setStatus(
          'Imagem importada'
        )


        await onImported()


        window.setTimeout(
          () => {
            onClose()
          },
          700,
        )
      } catch (err) {
        console.error(err)

        setStatus('')

        setError(
          err.message ||
          'Erro ao importar imagem.'
        )
      }
    }


  return (
    <div className="image-import-overlay">
      <div className="image-import-modal">
        <div className="image-import-header">
          <div>
            <span>
              IMAGE LIBRARY
            </span>

            <strong>
              Import Image
            </strong>
          </div>

          <button
            type="button"
            onClick={onClose}
          >
            ×
          </button>
        </div>


        <form
          className="image-import-form"
          onSubmit={handleSubmit}
        >
          <label>
            Compatible device

            <select
              value={templateId}
              onChange={(event) =>
                setTemplateId(
                  event.target.value
                )
              }
            >
              {importableDevices.map(
                (device) => (
                  <option
                    key={device.id}
                    value={device.id}
                  >
                    {device.name}
                    {' · '}
                    {device.vendor}
                  </option>
                )
              )}
            </select>
          </label>


          <label>
            Name

            <input
              type="text"
              placeholder="Ex: FortiOS 7.4"
              value={name}
              onChange={(event) =>
                setName(
                  event.target.value
                )
              }
            />
          </label>


          <div className="image-import-id">
            <span>
              Image ID
            </span>

            <strong>
              {generatedId || '-'}
            </strong>
          </div>


          <label>
            Vendor

            <input
              type="text"
              value={vendor}
              disabled
            />
          </label>


          <label>
            Version

            <input
              type="text"
              value={version}
              onChange={(event) =>
                setVersion(
                  event.target.value
                )
              }
            />
          </label>


          <label>
            Format

            <select
              value={imageFormat}
              onChange={(event) =>
                setImageFormat(
                  event.target.value
                )
              }
            >
              {allowedFormats.map(
                (format) => (
                  <option
                    key={format}
                    value={format}
                  >
                    {format}
                  </option>
                )
              )}
            </select>
          </label>


          <label>
            File

            <input
              type="file"
              accept={
                allowedFormats
                  .map(
                    (format) =>
                      `.${format}`
                  )
                  .join(',')
              }
              onChange={
                handleFileChange
              }
            />
          </label>


          {file && (
            <div className="image-import-file">
              <span>
                Selected file
              </span>

              <strong>
                {file.name}
              </strong>

              <small>
                {(
                  file.size /
                  (1024 ** 2)
                ).toFixed(1)}
                {' MB'}
              </small>
            </div>
          )}


          {error && (
            <div className="image-import-error">
              {error}
            </div>
          )}


          {status && (
            <div className="image-import-status">
              {status}
            </div>
          )}


          <div className="image-import-actions">
            <button
              type="button"
              className="image-import-cancel"
              onClick={onClose}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="image-import-submit"
              disabled={
                status ===
                'Importando imagem...'
              }
            >
              Import Image
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}


export default ImageImportModal
