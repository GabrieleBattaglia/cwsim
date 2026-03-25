# Piano di Implementazione: Modalità DX Expedition

L'obiettivo è introdurre in `cwsim` la modalità "DX Expedition" come alternativa alla modalità "Contest". Nella modalità DX Expedition, lo scambio dei numeri progressivi (NR) viene omesso e il QSO si conclude con la sola verifica del nominativo (Call) e del rapporto (RST).

Ecco i passaggi dettagliati per implementare questa nuova funzionalità:

## 1. Modifiche all'Interfaccia Grafica e Configurazione (COMPLETATO)
*   **`cwsimgui.ui`**: 
    *   Aggiunto un nuovo elemento per la scelta tra "Contest" e "DX Expedition" (il `typeComboBox`).
*   **`cwsim.py` (Gestione GUI)**:
    *   Collegato il nuovo selettore a una variabile per aggiornare il file di configurazione (`self.contest.isDxExpedition`).
*   **`contest.py` (Configurazione)**:
    *   Aggiunto un flag booleano `isDxExpedition` alla classe `Contest` (con supporto I/O config).

## 2. Modifiche alla Macchina a Stati dei Bot (Stazioni DX) (COMPLETATO)
Il cuore del comportamento delle stazioni chiamanti risiede in `dxoper.py` e `dxstation.py`. Attualmente, la macchina a stati si aspetta obbligatoriamente un NR.
*   **`dxstation.py`**:
    *   Passato il parametro `isDxExpedition` dalla classe `Contest` giù fino a `DxStation` e al suo `DxOperator`.
*   **`dxoper.py` (Classe `DxOperator`)**:
    *   Modificato il metodo `msgReceived()` (che analizza cosa hai trasmesso tu): se `isDxExpedition` è vera, la macchina a stati si ritiene soddisfatta saltando la richiesta del numero progressivo e passando a `NeedEnd`.
    *   Modificato il metodo `getReply()`: omesso l'invio del proprio NR se `isDxExpedition` è attiva.

## 3. Logica di Validazione del QSO dell'Utente (`cwsim.py`)
Il motore principale di log deve adattarsi all'assenza dell'NR.
*   **`saveQso()`**:
    *   Rimuovere l'obbligatorietà del campo `self._nr` nel controllo iniziale (`if not (self._hiscall and self._rst)`).
    *   Inserire un valore fittizio o vuoto nel log per quanto riguarda la colonna `Sent` o `Rcvd` del progressivo, senza che questo causi crash al simulatore.
*   **`checkQso()`**:
    *   Disabilitare il confronto di `self._lastLog[1] != self._lastQso[1]` (che rappresenta l'NR) quando la modalità DX Expedition è attiva.
*   **Motore di Pressione Tasti (`enter()` e `;`)**:
    *   Nella funzione `enter()`, quando l'operatore preme Invio, il sistema verifica se ha inviato Call e NR per passare allo stato successivo. Bisogna dire al sistema di non forzare l'invio del messaggio `StationMessage.NR` o del punto interrogativo se `isDxExpedition` è attiva e l'NR è assente.

## 4. Aggiornamento delle Statistiche Finali
*   **`writeSummary()` in `cwsim.py`**:
    *   L'intestazione del file TXT prodotto deve chiarire se la sessione era "Contest" o "DX Expedition".
    *   Quando si scansionano i log per riportare gli errori di scambio ("Exchanges miscopied"), la funzione non dovrà segnalare errore se l'NR è assente ma il resto è corretto.

---
**Sei d'accordo con questo approccio passo-passo?** Possiamo iniziare dalla modifica dell'interfaccia e della configurazione, per poi passare al motore a stati dei bot e infine alla validazione del log.
