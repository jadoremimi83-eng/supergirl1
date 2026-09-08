#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  CRM conversazionale SUPER GIRL. Verifica del nuovo flusso AI conversazionale e
  del nuovo stato pipeline "IN ATTESA DI CHIAMATA" (attesa_chiamata).
  L'AI (Andrea di J'adore Mimì) deve conversare in modo naturale (niente "Perfetto"
  ripetuto, mai la parola "AI", promo con scadenza dinamica) e, quando la cliente
  vuole prenotare, dire "Controllo le disponibilità e ti richiamo" e passare il lead
  allo stato attesa_chiamata (handoff allo staff, AI OFF, follow-up annullati, notifica).

backend:
  - task: "Nuovo stato pipeline attesa_chiamata"
    implemented: true
    working: "NA"
    file: "server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Aggiunto stato 'attesa_chiamata' (IN ATTESA DI CHIAMATA) a PIPELINE_STAGES (order 5). do_handoff con motivo=prenotazione ora porta il lead a attesa_chiamata (invece di da_fissare). home/priorities e filtro conversazioni 'da_fissare' includono ora sia attesa_chiamata sia da_fissare. Analytics conteggia attesa_chiamata come booking-ready. config/stages, pipeline verificati via curl."
  - task: "Flusso AI conversazionale naturale + handoff a attesa_chiamata"
    implemented: true
    working: "NA"
    file: "server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Verificato via curl: simulate-ai-turn con intenzione di prenotare -> handoff=True, motivo=prenotazione, new_status=attesa_chiamata, messaggio 'Benissimo! Controllo subito le disponibilità e ti richiamo...'. Reply naturale senza 'Perfetto'. Serve E2E completo (piu' turni) per verificare tono naturale, assenza parola 'AI', promo dinamica, e transizione corretta."

frontend:
  - task: "UI nuovo stato attesa_chiamata (pipeline, chat, scheda cliente)"
    implemented: true
    working: "NA"
    file: "theme.ts, pipeline.tsx, chat.tsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Aggiunto STAGES.attesa_chiamata (IN ATTESA DI CHIAMATA). Pipeline: colonna evidenziata (star) + espansa di default. Chat: badge star anche per attesa_chiamata + filtro 'Da fissare' include entrambi. Scheda cliente usa STAGES keys (picker automatico)."

metadata:
  created_by: "main_agent"
  version: "1.1"
  test_sequence: 4
  run_ui: false

test_plan:
  current_focus:
    - "Flusso AI conversazionale naturale + handoff a attesa_chiamata"
    - "Nuovo stato pipeline attesa_chiamata"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: |
        Testare il BACKEND del flusso AI (priorità). Credenziali admin@supergirl.app / Admin123!.
        Flusso E2E consigliato:
        1) POST /api/integrations/meta/simulate (admin) per creare un lead+conversazione (es. servizio "Bomba", senza sede).
        2) Simulare piu' turni cliente<->AI con POST /api/conversations/{id}/simulate-customer poi /simulate-ai-turn:
           - domanda generica -> AI risponde naturale, breve, UNA domanda.
           - domanda prezzo -> AI usa struttura listino/promo con scadenza dinamica (data futura).
           - VERIFICARE: l'AI non usa mai la parola "AI"/"assistente automatico"; non inizia sempre con "Perfetto"; non ripete la stessa apertura due volte di fila.
        3) Turno con intenzione di prenotare ("vorrei prenotare"/"fissare un appuntamento") -> /simulate-ai-turn deve tornare handoff=True, motivo="prenotazione", new_status="attesa_chiamata"; il lead passa a stato_pipeline=attesa_chiamata, conversazione ai_attiva=False, follow-up annullati, notifica creata.
        4) GET /api/pipeline deve includere lo stage attesa_chiamata; GET /api/home/priorities deve includere il lead in attesa_chiamata.
        Pulire (o segnalare) eventuali lead di test creati.
        NB: usato Emergent LLM key reale (GPT-5.4). Non mockato.
