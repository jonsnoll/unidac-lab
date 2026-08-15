import {
  useEffect,
  useState,
} from 'react'

import './ApplyPlanModal.css'


function getErrorMessage(data) {
  if (!data) {
    return 'Erro desconhecido.'
  }

  if (typeof data.detail === 'string') {
    return data.detail
  }

  if (
    data.detail &&
    typeof data.detail === 'object'
  ) {
    return (
      data.detail.message ||
      JSON.stringify(data.detail)
    )
  }

  return (
    data.message ||
    'A operacao falhou.'
  )
}


function ApplyPlanModal({
  onClose,
}) {
  const [plan, setPlan] =
    useState(null)

  const [loading, setLoading] =
    useState(true)

  const [applying, setApplying] =
    useState(false)

  const [result, setResult] =
    useState(null)

  const [error, setError] =
    useState('')


  useEffect(() => {
    let cancelled = false


    async function loadPlan() {
      setLoading(true)
      setError('')

      try {
        const response = await fetch(
          '/api/lab/apply-plan'
        )

        const data =
          await response.json()


        if (!response.ok) {
          throw new Error(
            getErrorMessage(data)
          )
        }


        if (!cancelled) {
          setPlan(data)
        }

      } catch (err) {
        if (!cancelled) {
          setError(
            err.message ||
            'Erro ao carregar Apply Plan.'
          )
        }

      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }


    loadPlan()


    return () => {
      cancelled = true
    }
  }, [])


  async function applyChanges() {
    if (
      !plan?.ready ||
      applying
    ) {
      return
    }


    setApplying(true)
    setError('')
    setResult(null)


    try {
      const response = await fetch(
        '/api/lab/apply',
        {
          method: 'POST',
        }
      )

      const data =
        await response.json()


      if (!response.ok) {
        throw new Error(
          getErrorMessage(data)
        )
      }


      setResult(data)

    } catch (err) {
      setError(
        err.message ||
        'Erro ao aplicar laboratorio.'
      )

    } finally {
      setApplying(false)
    }
  }


  function closeAndRefresh() {
    window.location.reload()
  }


  return (
    <div className="apply-overlay">
      <div className="apply-modal">
        <div className="apply-header">
          <div>
            <strong>
              Apply Changes
            </strong>

            <span>
              Desired → Real
            </span>
          </div>

          <button
            type="button"
            className="apply-close"
            onClick={onClose}
            disabled={applying}
          >
            ×
          </button>
        </div>


        <div className="apply-body">
          {loading && (
            <div className="apply-loading">
              Calculando Apply Plan...
            </div>
          )}


          {error && (
            <div className="apply-error">
              {error}
            </div>
          )}


          {!loading && plan && (
            <>
              <div
                className={
                  plan.ready
                    ? 'apply-readiness ready'
                    : 'apply-readiness blocked'
                }
              >
                <strong>
                  {plan.ready
                    ? 'READY'
                    : 'BLOCKED'}
                </strong>

                <span>
                  {plan.ready
                    ? 'Plano liberado para execução'
                    : 'Corrija os erros antes do Apply'}
                </span>
              </div>


              <div className="apply-summary">
                <div>
                  <strong>
                    {plan.summary.nodes}
                  </strong>
                  <span>Nodes</span>
                </div>

                <div>
                  <strong>
                    {plan.summary.links}
                  </strong>
                  <span>Links</span>
                </div>

                <div>
                  <strong>
                    {plan.summary.errors}
                  </strong>
                  <span>Errors</span>
                </div>

                <div>
                  <strong>
                    {plan.summary.warnings}
                  </strong>
                  <span>Warnings</span>
                </div>
              </div>


              {plan.errors.length > 0 && (
                <section className="apply-section">
                  <h3>Errors</h3>

                  {plan.errors.map(
                    (item, index) => (
                      <div
                        className="apply-message error"
                        key={
                          `${item.type}-${index}`
                        }
                      >
                        {item.message}
                      </div>
                    )
                  )}
                </section>
              )}


              {plan.warnings.length > 0 && (
                <section className="apply-section">
                  <h3>Warnings</h3>

                  {plan.warnings.map(
                    (item, index) => (
                      <div
                        className="apply-message warning"
                        key={
                          `${item.type}-${index}`
                        }
                      >
                        {item.message}
                      </div>
                    )
                  )}
                </section>
              )}


              <section className="apply-section">
                <h3>Execution Plan</h3>

                <div className="apply-actions">
                  {plan.actions.map(
                    (action) => (
                      <div
                        className="apply-action"
                        key={
                          `${action.node_id}-${action.action}`
                        }
                      >
                        <div>
                          <strong>
                            {action.node_name}
                          </strong>

                          <span>
                            {action.action}
                          </span>
                        </div>

                        <code>
                          {
                            action.domain_name ||
                            action.libvirt_network ||
                            '-'
                          }
                        </code>
                      </div>
                    )
                  )}
                </div>
              </section>
            </>
          )}


          {result && (
            <div className="apply-success">
              <strong>
                Apply concluído
              </strong>

              <span>
                {result.executed} etapas executadas.
              </span>


              <div className="apply-results">
                {result.results.map(
                  (item, index) => (
                    <div
                      key={
                        `${item.step}-${index}`
                      }
                    >
                      <span>
                        {item.step}
                      </span>

                      <strong>
                        {item.node_name}
                      </strong>

                      <code>
                        {item.result.status}
                        {item.result.state
                          ? ` / ${item.result.state}`
                          : ''}
                      </code>
                    </div>
                  )
                )}
              </div>
            </div>
          )}
        </div>


        <div className="apply-footer">
          {!result && (
            <>
              <button
                type="button"
                className="apply-secondary"
                onClick={onClose}
                disabled={applying}
              >
                Cancel
              </button>

              <button
                type="button"
                className="apply-primary"
                onClick={applyChanges}
                disabled={
                  loading ||
                  applying ||
                  !plan?.ready
                }
              >
                {applying
                  ? 'Applying...'
                  : 'Apply Now'}
              </button>
            </>
          )}


          {result && (
            <button
              type="button"
              className="apply-primary"
              onClick={
                closeAndRefresh
              }
            >
              Close and Refresh
            </button>
          )}
        </div>
      </div>
    </div>
  )
}


export default ApplyPlanModal
