          (() => {
            const tbody = document.getElementById('pending-push-logs-body');
            const emptyRow = document.getElementById('empty-push-logs-row');
            const hasVisibleRows = tbody?.querySelector('[data-log-row]');

            if (emptyRow) {
              emptyRow.classList.toggle('hidden', Boolean(hasVisibleRows));
            }
          })();
        
