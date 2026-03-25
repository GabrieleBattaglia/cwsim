def CWzator(msg, wpm=35, pitch=550, l=30, s=50, p=50, fs=44100, ms=1, vol=0.5, wv=1, sync=False, file=False):
	"""
	V8.2 di mercoledì 28 maggio 2025 - Gabriele Battaglia (IZ4APU), Claude 3.5, ChatGPT o3-mini-high, Gemini 2.5 Pro
		da un'idea originale di Kevin Schmidt W9CF
	Genera e riproduce l'audio del codice Morse dal messaggio di testo fornito.
	Parameters:
		msg (str|int): Messaggio di testo da convertire in Morse.
			se == -1 restituisce la mappa	morse come dizionario.
		wpm (int): Velocità in parole al minuto (range 5-100).
		pitch (int): Frequenza in Hz per il tono (range 130-2800).
		l (int): Peso per la durata della linea (default 30).
		s (int): Peso per la durata degli spazi tra simboli/lettere (default 50).
		p (int): Peso per la durata del punto (default 50).
		fs (int): Frequenza di campionamento (default 44100 Hz).
		ms (int): Durata in millisecondi per i fade-in/out sui toni (default 1).
		vol (float): Volume (range 0.0 a 1.0, default 0.5).
		wv (int): Tipo d’onda (scipy.signal): 1=Sine(default), 2=Square, 3=Triangle, 4=Sawtooth.
		sync (bool): Se True, la funzione aspetta la fine della riproduzione; altrimenti ritorna subito.
		file (bool): Se True, salva l’audio in un file WAV.
	Returns:
		Un oggetto PlaybackHandle e rwpm (velocità effettiva wpm), o (None, None) in caso di errore.
	"""
	import numpy as np
	import sounddevice as sd
	import wave
	from datetime import datetime
	import threading
	import sys
	from scipy import signal # Importato per le forme d'onda
	BLOCK_SIZE = 256
	MORSE_MAP = {
		"a":".-", "b":"-...", "c":"-.-.", "d":"-..", "e":".", "f":"..-.",
		"g":"--.", "h":"....", "i":"..", "j":".---", "k":"-.-", "l":".-..",
		"m":"--", "n":"-.", "o":"---", "p":".--.", "q":"--.-", "r":".-.",
		"s":"...", "t":"-", "u":"..-", "v":"...-", "w":".--", "x":"-..-",
		"y":"-.--", "z":"--..", "0":"-----", "1":".----", "2":"..---",
		"3":"...--", "4":"....-", "5":".....", "6":"-....", "7":"--...",
		"8":"---..", "9":"----.", ".":".-.-.-", "-":"-....-", ",":"--..--",
		"?":"..--..", "/":"-..-.", ";":"-.-.-.", "(":"-.--.", "[":"-.--.",
		")":"-.--.-", "]":"-.--.-", "@":".--.-.", "*":"...-.-", "+":".-.-.",
		"%":".-...", ":":"---...", "=":"-...-", '"':".-..-.", "'":".----.",
		"!":"-.-.--", "$":"...-..-", " ":"", "_":"",
		"ò":"---.", "à":".--.-", "ù":"..--", "è":"..-..",
		"é":"..-..", "ì":".---."}
	if msg==-1: return MORSE_MAP
	elif not isinstance(msg, str) or msg == "": print("CWzator Error: msg deve essere una stringa non vuota.", file=sys.stderr); return None, None
	if not (isinstance(wpm, int) and 5 <= wpm <= 100): print(f"CWzator Error: wpm ({wpm}) non valido [5-100].", file=sys.stderr); return None, None
	if not (isinstance(pitch, int) and 130 <= pitch <= 2800): print(f"CWzator Error: pitch ({pitch}) non valido [130-2000].", file=sys.stderr); return None, None
	if not (isinstance(l, int) and 1 <= l <= 100): print(f"CWzator Error: l ({l}) non valido [1-100].", file=sys.stderr); return None, None
	if not (isinstance(s, int) and 1 <= s <= 100): print(f"CWzator Error: s ({s}) non valido [1-100].", file=sys.stderr); return None, None
	if not (isinstance(p, int) and 1 <= p <= 100): print(f"CWzator Error: p ({p}) non valido [1-100].", file=sys.stderr); return None, None
	if not (isinstance(fs, int) and fs > 0): print(f"CWzator Error: fs ({fs}) non valido [>0].", file=sys.stderr); return None, None
	if not (isinstance(ms, (int, float)) and ms >= 0): print(f"CWzator Error: ms ({ms}) non valido [>=0].", file=sys.stderr); return None, None
	if not (isinstance(vol, (int, float)) and 0.0 <= vol <= 1.0): print(f"CWzator Error: vol ({vol}) non valido [0.0-1.0].", file=sys.stderr); return None, None
	if not (isinstance(wv, int) and wv in [1, 2, 3, 4]): print(f"CWzator Error: wv ({wv}) non valido [1-4].", file=sys.stderr); return None, None
	# --- Calcolo Durate (con arrotondamento campioni implicito dopo) ---
	T = 1.2 / float(wpm)
	dot_duration = T * (p / 50.0)
	dash_duration = 3.0 * T * (l / 30.0) # Usato 3.0 per float
	intra_gap = T * (s / 50.0)
	letter_gap = 3.0 * T * (s / 50.0)
	word_gap = 7.0 * T * (s / 50.0)
	# --- Funzioni Generazione Segmenti (con forme d'onda scipy e arrotondamento) ---
	def generate_tone(duration):
		# Arrotonda qui per il numero di campioni
		N = int(round(fs * duration))
		if N <= 0: return np.array([], dtype=np.int16) # Ritorna array vuoto se durata troppo breve
		# Usa float64 per tempo e fase per precisione
		t = np.linspace(0, duration, N, endpoint=False, dtype=np.float64)
		# Forme d'onda via scipy.signal (output in [-1, 1])
		if wv == 1:  # Sine
			signal_float = np.sin(2 * np.pi * pitch * t)
		elif wv == 2:  # Square
			signal_float = signal.square(2 * np.pi * pitch * t)
		elif wv == 3:  # Triangle (width=0.5)
			signal_float = signal.sawtooth(2 * np.pi * pitch * t, width=0.5)
		else:  # Sawtooth (width=1)
			signal_float = signal.sawtooth(2 * np.pi * pitch * t, width=1)
		signal_float = signal_float.astype(np.float32) # Converti a float32 per audio
		# Applica Fade In/Out
		fade_samples = int(round(fs * ms / 1000.0)) # Arrotonda campioni fade
		# Condizione robusta per sovrapposizione fade
		if fade_samples > 0 and fade_samples <= N // 2:
			ramp = np.linspace(0, 1, fade_samples, dtype=np.float32)
			signal_float[:fade_samples] *= ramp
			signal_float[-fade_samples:] *= ramp[::-1] # Usa slicing negativo per l'ultimo pezzo
		# Applica volume e converti a int16
		# Clipping prima della conversione int16
		signal_float = np.clip(signal_float * vol, -1.0, 1.0)
		return (signal_float * 32767.0).astype(np.int16)
	def generate_silence(duration):
		# Arrotonda qui per il numero di campioni
		N = int(round(fs * duration))
		return np.zeros(N, dtype=np.int16) if N > 0 else np.array([], dtype=np.int16)
	# --- Assemblaggio Sequenza (invariato) ---
	segments = []
	words = msg.lower().split()
	for w_idx, word in enumerate(words):
		# Usa una stringa per accumulare le lettere valide invece di una lista
		valid_letters = "".join(ch for ch in word if ch in MORSE_MAP)
		for l_idx, letter in enumerate(valid_letters):
			code = MORSE_MAP.get(letter) # Usa .get() per sicurezza? No, già filtrato.
			if not code: continue # Salta se per qualche motivo non c'è codice (non dovrebbe succedere)
			for s_idx, symbol in enumerate(code):
				if symbol == '.':
					segments.append(generate_tone(dot_duration))
				elif symbol == '-':
					segments.append(generate_tone(dash_duration))
				# Aggiungi gap intra-simbolo solo se non è l'ultimo simbolo
				if s_idx < len(code) - 1:
					segments.append(generate_silence(intra_gap))
			# Aggiungi gap tra lettere solo se non è l'ultima lettera
			if l_idx < len(valid_letters) - 1:
				segments.append(generate_silence(letter_gap))
		# Aggiungi gap tra parole solo se non è l'ultima parola
		if w_idx < len(words) - 1:
			# Controlla se la parola precedente non era solo spazi o caratteri ignorati
			if valid_letters or any(ch in MORSE_MAP for ch in words[w_idx+1]):
				segments.append(generate_silence(word_gap))
	# --- Concatenazione e Aggiunta Silenzio Finale ---
	audio = np.concatenate(segments) if segments else np.array([], dtype=np.int16)
	if audio.size > 0: # Aggiungi solo se c'è audio
		silence_samples_end = int(round(fs * 0.005)) # Es. 5ms di silenzio finale
		if silence_samples_end > 0:
			final_silence = np.zeros(silence_samples_end, dtype=np.int16)
			audio = np.concatenate((audio, final_silence))
	# --- Calcolo rwpm (con gestione divisione per zero robusta) ---
	rwpm = wpm # Default se pesi standard o nessun elemento contato
	if (l, s, p) != (30, 50, 50):
		dots = dashes = intra_gaps = letter_gaps = word_gaps = 0
		words_list = msg.lower().split()
		processed_letters_count = 0 # Contatore per gestire gaps
		for w_idx, w in enumerate(words_list):
			current_word_letters = 0
			code_lengths_in_word = []
			for letter in w:
				if letter in MORSE_MAP:
					code = MORSE_MAP[letter]
					if code: # Ignora spazi o caratteri mappati a stringa vuota
						dots += code.count('.')
						dashes += code.count('-')
						code_len = len(code)
						if code_len > 1:
							intra_gaps += (code_len - 1)
						code_lengths_in_word.append(code_len)
						current_word_letters += 1
			if current_word_letters > 1:
				letter_gaps += (current_word_letters - 1)
			processed_letters_count += current_word_letters
			# Aggiungi word gap solo se la parola conteneva elementi e non è l'ultima
			if current_word_letters > 0 and w_idx < len(words_list) - 1:
				# E controlla anche se la parola successiva contiene elementi
				if any(ch in MORSE_MAP and MORSE_MAP[ch] for ch in words_list[w_idx+1]):
					word_gaps += 1
		# Calcola durate totali (in unità di dot)
		# Durata standard: 1 (dot) + 1 (gap) = 2, 3 (dash) + 1 (gap) = 4
		# Gap tra lettere = 3, Gap tra parole = 7
		# L'unità base è la durata del dot standard (T * p/50 dove p=50)
		standard_total_units = dots + 3*dashes + intra_gaps + 3*letter_gaps + 7*word_gaps
		# Durata attuale con pesi
		actual_dot_units = p / 50.0
		actual_dash_units = 3.0 * (l / 30.0)
		actual_intra_gap_units = s / 50.0
		actual_letter_gap_units = 3.0 * (s / 50.0)
		actual_word_gap_units = 7.0 * (s / 50.0)
		actual_total_units = (dots * actual_dot_units) + \
							 (dashes * actual_dash_units) + \
							 (intra_gaps * actual_intra_gap_units) + \
							 (letter_gaps * actual_letter_gap_units) + \
							 (word_gaps * actual_word_gap_units)
		# Calcola rapporto e rwpm solo se ci sono state durate
		if standard_total_units > 0 and actual_total_units > 0:
			ratio = actual_total_units / standard_total_units
			rwpm = wpm / ratio
		elif standard_total_units == 0 and actual_total_units == 0:
			rwpm = wpm # Messaggio vuoto, rwpm è uguale a wpm nominale
		else:
			# Caso anomalo (es. solo spazi?), imposta rwpm a wpm o 0?
			# Manteniamo wpm per ora, ma potrebbe essere indice di errore input.
			rwpm = wpm
			print("CWzator Warning: Calcolo rwpm anomalo, possibile input solo con spazi?", file=sys.stderr)
	# --- Classe PlaybackHandle (invariata ma ora riceve audio con silenzio finale) ---
	class PlaybackHandle:
		def __init__(self, audio_data, sample_rate):
			self.audio_data = audio_data
			self.sample_rate = sample_rate
			self.stream = None
			self.is_playing = threading.Event() # Usa Event per thread-safety
			self._thread = None # Riferimento al thread
		def _playback_target(self):
			"""Target function per il thread di riproduzione."""
			self.is_playing.set() # Segnala inizio riproduzione
			stream = None # Inizializza per blocco finally
			try:
				with sd.OutputStream(
					samplerate=self.sample_rate, channels=1, dtype=np.int16,
					blocksize=BLOCK_SIZE, latency='low'
				) as stream:
					# Salva riferimento allo stream *dopo* che è stato creato con successo
					self.stream = stream
					# Scrittura a blocchi, controllando il flag ad ogni blocco
					for i in range(0, len(self.audio_data), BLOCK_SIZE):
						if not self.is_playing.is_set(): # Controlla l'evento
							# print("Debug: Stop richiesto durante la riproduzione.")
							stream.stop() # Prova a fermare lo stream corrente
							break
						block = self.audio_data[i:min(i + BLOCK_SIZE, len(self.audio_data))]
						stream.write(block)
					# Se il loop finisce normalmente, attendi che lo stream finisca l'output bufferizzato
					if self.is_playing.is_set():
						# print("Debug: Loop terminato, attendo stream.close() implicito.")
						pass # 'with' gestisce la chiusura e l'attesa implicita
			except sd.PortAudioError as pae:
				print(f"CWzator Playback PortAudioError: {pae}", file=sys.stderr)
			except Exception as e:
				print(f"CWzator Playback Error: {e}", file=sys.stderr)
			finally:
				# print("Debug: Uscita blocco try/finally _playback_target.")
				self.is_playing.clear() # Segnala fine riproduzione o errore
				self.stream = None # Rilascia riferimento allo stream
		def play(self):
			"""Avvia la riproduzione in un thread separato."""
			if not self.is_playing.is_set() and self.audio_data.size > 0:
				# Crea e avvia il thread solo se non sta già suonando e c'è audio
				self._thread = threading.Thread(target=self._playback_target)
				self._thread.daemon = False # Assicura non-daemon
				self._thread.start()
			# else: print("Debug: Play chiamato ma già in esecuzione o audio vuoto.")
		def wait_done(self):
			"""Attende la fine della riproduzione corrente."""
			# Attende che l'evento is_playing sia clear O che il thread termini
			if self._thread is not None and self._thread.is_alive():
				# print("Debug: wait_done chiamato, joining thread...")
				self._thread.join()
			# print("Debug: wait_done terminato.")
		def stop(self):
			"""Richiede l'interruzione della riproduzione."""
			# print("Debug: stop richiesto.")
			self.is_playing.clear() # Segnala al loop di playback di fermarsi
			# Nota: l'interruzione effettiva dipende da quanto velocemente il loop
			# controlla l'evento e da quanto tempo impiega stream.stop().
			# Non chiudiamo lo stream qui, il blocco 'with' lo farà.
	# --- Creazione Oggetto e Avvio Playback (Logica Originale) ---
	play_obj = PlaybackHandle(audio, fs)
	# Avvia la riproduzione nel thread interno all'oggetto
	play_obj.play() # Il metodo play ora gestisce l'avvio del thread
	# --- Salvataggio File (invariato) ---
	if file:
		filename = f"cwapu Morse recorded at {datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
		try:
			with wave.open(filename, 'wb') as wf:
				wf.setnchannels(1) # Mono
				wf.setsampwidth(2) # 16-bit
				wf.setframerate(fs)
				wf.writeframes(audio.tobytes())
			# print(f"CWzator: Audio salvato in {filename}")
		except Exception as e:
			print(f"CWzator Error durante salvataggio file: {e}", file=sys.stderr)
	# --- Gestione Sync (usa wait_done dell'oggetto) ---
	if sync:
		play_obj.wait_done() # Usa il metodo dell'oggetto per attendere
	# --- Ritorno Oggetto e rwpm ---
	return play_obj, rwpm

class Mazzo:
	'''
	V5.2 - settembre 2025 b Gabriele Battaglia & Gemini 2.5
	Classe autocontenuta che rappresenta un mazzo di carte italiano o francese,
	con supporto per mazzi multipli, mescolamento, pesca con rimescolamento
	automatico degli scarti, e gestione flessibile delle carte.
	Non produce output diretto (print), ma restituisce valori o stringhe informative.
	'''
	import random
	from collections import namedtuple
	Carta = namedtuple("Carta", ["id", "nome", "valore", "seme_nome", "seme_id", "desc_breve"])
	_SEMI_FRANCESI = ["Cuori", "Quadri", "Fiori", "Picche"]
	_SEMI_ITALIANI = ["Bastoni", "Spade", "Coppe", "Denari"]
	_VALORI_FRANCESI = [("Asso", 1)] + [(str(i), i) for i in range(2, 11)] + [("Jack", 11), ("Regina", 12), ("Re", 13)]
	_VALORI_ITALIANI = [("Asso", 1)] + [(str(i), i) for i in range(2, 8)] + [("Fante", 8), ("Cavallo", 9), ("Re", 10)]
	_VALORI_DESCRIZIONE = {1: 'A', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: '0', 11: 'J', 12: 'Q', 13: 'K'}
	_SEMI_DESCRIZIONE = {"Cuori": 'C', "Quadri": 'Q', "Fiori": 'F', "Picche": 'P',
																						"Bastoni": 'B', "Spade": 'S', "Coppe": 'O', "Denari": 'D'} # 'O' per Coppe
	def __init__(self, tipo_francese=True, num_mazzi=1):
		'''
		Inizializza uno o più mazzi di carte.
		Parametri:
		- tipo_francese (bool): True per mazzo francese (default), False per mazzo italiano.
		- num_mazzi (int): Numero di mazzi da includere (default 1). Deve essere >= 1.
		'''
		if not isinstance(num_mazzi, int) or num_mazzi < 1:
			raise ValueError("Il numero di mazzi deve essere un intero maggiore o uguale a 1.")
		self.tipo_francese = tipo_francese
		self.num_mazzi = num_mazzi
		# Liste per tracciare lo stato delle carte
		self.carte = [] # Mazzo principale da cui pescare
		self.scarti = [] # Pila degli scarti, possono essere rimescolati
		self.scarti_permanenti = [] # Carte rimosse permanentemente
		self._costruisci_mazzo()
	def _costruisci_mazzo(self):
		'''
		(Metodo privato) Costruisce il mazzo di carte in base al tipo e al numero di mazzi.
		'''
		self.carte = [] # Resetta il mazzo
		semi = self._SEMI_FRANCESI if self.tipo_francese else self._SEMI_ITALIANI
		valori = self._VALORI_FRANCESI if self.tipo_francese else self._VALORI_ITALIANI
		id_carta_counter = 1
		for _ in range(self.num_mazzi):
			for id_seme, nome_seme in enumerate(semi, 1):
				# Correzione: L'ID seme per mazzi italiani dovrebbe partire da 5 per distinguerli?
				# No, l'ID seme è relativo al tipo di mazzo (1-4 per entrambi),
				# il nome_seme è ciò che li distingue. Manteniamo 1-4.
				seme_id_effettivo = id_seme
				if not self.tipo_francese:
					# Se si volesse un ID globale unico (1-4 Francese, 5-8 Italiano)
					# seme_id_effettivo = id_seme + 4 # Questa è un'opzione di design, ma la lasciamo 1-4 per ora
					pass # Manteniamo 1-4 come da codice originale
				for nome_valore, valore_num in valori:
					desc_val = self._VALORI_DESCRIZIONE.get(valore_num, '?')
					desc_seme = self._SEMI_DESCRIZIONE.get(nome_seme, '?')
					desc_breve = f"{desc_val}{desc_seme}"
					nome_completo = f"{nome_valore} di {nome_seme}"
					# Usiamo la definizione di Carta interna alla classe
					carta = self.Carta(id=id_carta_counter,
																								nome=nome_completo,
																								valore=valore_num,
																								seme_nome=nome_seme,
																								seme_id=seme_id_effettivo,
																								desc_breve=desc_breve)
					self.carte.append(carta)
					id_carta_counter += 1
	def mescola_mazzo(self):
		'''
		Mescola le carte nel mazzo principale (self.carte).
		Non restituisce nulla.
		'''
		if not self.carte:
			return # Non fare nulla se il mazzo è vuoto
		self.random.shuffle(self.carte)
	def pesca(self, quante=1):
		'''
		Pesca carte dal mazzo principale. Se le carte nel mazzo non sono sufficienti,
		rimescola automaticamente gli scarti prima di pescare.
		Le carte pescate vengono spostate nella lista 'pescate'.
		Parametri:
		- quante (int): Numero di carte da pescare (default 1).
		Ritorna:
		- list[Carta]: Lista delle carte pescate. Può contenere meno carte di 'quante'
									 se il mazzo e gli scarti combinati non sono sufficienti.
		'''
		if quante < 0:
			raise ValueError("Il numero di carte da pescare deve essere non negativo.")
		if quante == 0:
			return []
		# NUOVA LOGICA: Se le carte nel mazzo sono meno di quelle richieste, rimescola gli scarti.
		if len(self.carte) < quante and self.scarti:
			print("\n--- Carte insufficienti nel mazzo. Rimescolo gli scarti... ---") # Feedback utile per il giocatore
			self.carte.extend(self.scarti)
			self.scarti = []
			self.mescola_mazzo()
			print(f"--- Rimescolamento completato. Carte nel mazzo: {len(self.carte)} ---")
		# Ora procedi con la pesca
		num_da_pescare = min(quante, len(self.carte))
		carte_pescate_ora = []
		if num_da_pescare > 0:
			for _ in range(num_da_pescare):
				carte_pescate_ora.append(self.carte.pop())
		return carte_pescate_ora
	def scarta_carte(self, carte_da_scartare):
		'''
		Aggiunge una lista di carte alla pila degli scarti.
		Parametri:
		- carte_da_scartare (list[Carta]): Lista di oggetti Carta da spostare negli scarti.
		'''
		if not carte_da_scartare:
			return
		self.scarti.extend(carte_da_scartare)
	def rimescola_scarti(self, include_pescate=False):
		'''
		Rimette le carte dalla pila degli scarti nel mazzo principale e mescola.
		Opzionalmente, può includere anche le carte attualmente pescate.
		Non reintegra le carte scartate permanentemente.
		Parametri:
		- include_pescate (bool): Se True, anche le carte in self.pescate sono rimesse (default False).
		Ritorna:
		- str: Messaggio che riepiloga l'operazione.
		'''
		carte_da_reintegrare = []
		msg_parts = []
		num_scarti = len(self.scarti)
		if num_scarti > 0:
			carte_da_reintegrare.extend(self.scarti)
			self.scarti = []
			msg_parts.append(f"{num_scarti} scarti reintegrati.")
		else:
			msg_parts.append("Nessuno scarto da reintegrare.")
		num_pescate = len(self.pescate)
		if include_pescate:
			if num_pescate > 0:
				carte_da_reintegrare.extend(self.pescate)
				self.pescate = []
				msg_parts.append(f"{num_pescate} carte pescate reintegrate.")
			else:
				msg_parts.append("Nessuna carta pescata da reintegrare.")
		if not carte_da_reintegrare:
			return "Nessuna carta da rimescolare. " + " ".join(msg_parts)
		self.carte.extend(carte_da_reintegrare)
		self.mescola_mazzo()
		msg_parts.append(f"Mazzo ora contiene {len(self.carte)} carte.")
		return " ".join(msg_parts)
	def _rimuovi_carte_da_lista(self, lista_sorgente, condizione, destinazione, nome_destinazione):
		''' Funzione helper per rimuovere carte da una lista in base a una condizione. '''
		carte_da_mantenere = []
		carte_rimosse = []
		for carta in lista_sorgente:
			if condizione(carta):
				carte_rimosse.append(carta)
			else:
				carte_da_mantenere.append(carta)
		if carte_rimosse:
			destinazione.extend(carte_rimosse)
			# Modifica la lista originale inplace
			lista_sorgente[:] = carte_da_mantenere
		return carte_rimosse
	def rimuovi_semi(self, semi_id_da_rimuovere, permanente=False):
		'''
		Rimuove dal mazzo principale (self.carte) tutte le carte con i semi specificati.
		Le carte rimosse vengono spostate negli scarti temporanei o permanenti.
		Parametri:
		- semi_id_da_rimuovere (list[int]): Lista di ID numerici dei semi da rimuovere.
		- permanente (bool): Se True, sposta in scarti_permanenti, altrimenti in scarti (default False).
		Ritorna:
		- int: Numero di carte rimosse dal mazzo principale.
		'''
		destinazione = self.scarti_permanenti if permanente else self.scarti
		nome_dest = "permanenti" if permanente else "temporanei"
		condizione = lambda carta: carta.seme_id in semi_id_da_rimuovere
		carte_rimosse = self._rimuovi_carte_da_lista(self.carte, condizione, destinazione, nome_dest)
		return len(carte_rimosse)
	def rimuovi_valori(self, valori_da_rimuovere, permanente=True):
		'''
		Rimuove dal mazzo principale (self.carte) tutte le carte con i valori specificati.
		Le carte rimosse vengono spostate negli scarti permanenti o temporanei.
		Parametri:
		- valori_da_rimuovere (list[int]): Lista di valori numerici da rimuovere.
		- permanente (bool): Se True, sposta in scarti_permanenti (default), altrimenti in scarti.
		Ritorna:
		- int: Numero di carte rimosse dal mazzo principale.
		'''
		destinazione = self.scarti_permanenti if permanente else self.scarti
		nome_dest = "permanenti" if permanente else "temporanei"
		condizione = lambda carta: carta.valore in valori_da_rimuovere
		carte_rimosse = self._rimuovi_carte_da_lista(self.carte, condizione, destinazione, nome_dest)
		return len(carte_rimosse)
	def aggiungi_jolly(self, quanti_per_mazzo=2):
		'''
		Aggiunge jolly al mazzo principale fino a raggiungere il numero corretto
		per ogni mazzo originale (quanti_per_mazzo * num_mazzi).
		Funziona solo per mazzi di tipo francese. Jolly esistenti non vengono duplicati.
		Parametri:
		- quanti_per_mazzo (int): Numero di jolly desiderato per ciascun mazzo originale (default 2).
		Ritorna:
		- str: Messaggio che indica quanti jolly sono stati aggiunti o se erano già presenti.
		'''
		if not self.tipo_francese:
			return "I jolly possono essere aggiunti solo ai mazzi di tipo francese."
		if quanti_per_mazzo < 0:
			# Non ha senso avere un numero negativo di jolly per mazzo
			return "Numero di jolly per mazzo non valido (deve essere >= 0)."

		# Calcola il numero totale di jolly che dovrebbero esserci
		jolly_attesi_totali = self.num_mazzi * quanti_per_mazzo
		# Controlla quanti jolly esistono già in *tutte* le liste
		all_cards = self.carte + self.pescate + self.scarti + self.scarti_permanenti
		jolly_esistenti_count = sum(1 for c in all_cards if c.nome == "Jolly")
		# Determina quanti jolly mancano (se ce ne sono)
		jolly_da_aggiungere = jolly_attesi_totali - jolly_esistenti_count
		if jolly_da_aggiungere <= 0:
			# Se non ne mancano o ce ne sono addirittura di più (improbabile ma gestito)
			return f"Nessun nuovo jolly aggiunto (numero richiesto: {jolly_attesi_totali}, già presenti: {jolly_esistenti_count})."
		# Se dobbiamo aggiungere jolly:
		# Trova l'ID massimo attuale per continuare la sequenza
		max_id = 0
		if all_cards:
			ids = [c.id for c in all_cards if c.id is not None]
			if ids:
				max_id = max(ids)
		jolly_aggiunti_count = 0
		for i in range(jolly_da_aggiungere):
			jolly_id = max_id + 1 + i
			# Crea il jolly e aggiungilo al mazzo principale
			jolly = self.Carta(id=jolly_id, nome="Jolly", valore=None, seme_nome="N/A", seme_id=0, desc_breve="XY")
			self.carte.append(jolly)
			jolly_aggiunti_count += 1
			# Aggiorna max_id per il prossimo ciclo (se ce n'è più di uno)
			max_id = jolly_id
		if jolly_aggiunti_count > 0:
			return f"Aggiunti {jolly_aggiunti_count} jolly al mazzo principale."
		else:
			# Questo caso non dovrebbe verificarsi data la logica precedente, ma per sicurezza
			return "Nessun nuovo jolly aggiunto."
	def rimuovi_jolly(self, permanente=False):
		'''
		Rimuove tutti i jolly dalle pile modificabili (mazzo, pescate, e scarti se permanente=True)
		e li sposta nella destinazione appropriata (scarti temporanei o permanenti).
		Parametri:
		- permanente (bool): Se True, sposta in scarti_permanenti e pulisce anche gli scarti temporanei.
		                     Se False, sposta solo in scarti temporanei.
		Ritorna:
		- str: Messaggio che indica quanti jolly unici sono stati rimossi e dove sono stati spostati.
		'''
		jolly_rimossi_total_obj = [] # Lista per collezionare gli oggetti jolly rimossi
		destinazione = self.scarti_permanenti if permanente else self.scarti
		tipo_destinazione = "permanenti" if permanente else "temporanei"
		condizione = lambda carta: carta.nome == "Jolly"
		# Helper per evitare codice duplicato e gestire la collezione degli oggetti
		def _processa_lista(lista_sorgente):
			carte_rimosse = self._rimuovi_carte_da_lista(lista_sorgente, condizione, destinazione, tipo_destinazione)
			jolly_rimossi_total_obj.extend(carte_rimosse)
		# Rimuove da self.carte
		_processa_lista(self.carte)
		# Rimuove da self.pescate
		_processa_lista(self.pescate)
		# Rimuove da self.scarti SOLO SE la destinazione NON è self.scarti
		# Questo previene che gli elementi appena aggiunti a self.scarti vengano rimossi di nuovo.
		if permanente:
			_processa_lista(self.scarti) # Pulisce gli scarti temporanei spostando i jolly in quelli permanenti
		# Calcola quanti jolly unici sono stati effettivamente spostati
		# Utile se per errore un jolly fosse presente in più liste (non dovrebbe accadere)
		num_rimossi_unici = len({j.id for j in jolly_rimossi_total_obj})
		if num_rimossi_unici > 0:
			return f"Rimossi {num_rimossi_unici} jolly unici. Spostati negli scarti {tipo_destinazione}."
		else:
			return "Nessun jolly trovato da rimuovere."
	def _rimuovi_carte_da_lista(self, lista_sorgente, condizione, destinazione, nome_destinazione):
		''' Funzione helper per rimuovere carte da una lista in base a una condizione. '''
		carte_da_mantenere = []
		carte_rimosse = []
		for carta in lista_sorgente:
			if condizione(carta):
				carte_rimosse.append(carta)
			else:
				carte_da_mantenere.append(carta)
		if carte_rimosse:
			# Aggiunge gli elementi rimossi alla lista di destinazione
			destinazione.extend(carte_rimosse)
			# Modifica la lista originale inplace rimuovendo gli elementi
			lista_sorgente[:] = carte_da_mantenere
			# Ritorna la lista degli elementi rimossi
		return carte_rimosse
	def stato_mazzo(self):
		''' Ritorna una stringa che riepiloga lo stato attuale del mazzo. '''
		return (f"Mazzo: {len(self.carte)} carte | "
				f"Scarti: {len(self.scarti)} carte | "
				f"Scarti Permanenti: {len(self.scarti_permanenti)} carte")
	def __len__(self):
		''' Ritorna il numero di carte attualmente nel mazzo principale (self.carte). '''
		return len(self.carte)
	def __str__(self):
		''' Rappresentazione stringa dell'oggetto Mazzo (mostra lo stato). '''
		return self.stato_mazzo()
	def mostra_carte(self, lista='mazzo'):
		'''
		Restituisce una stringa con le descrizioni brevi delle carte
		in una specifica lista (mazzo, pescate, scarti, permanenti).
		Parametri:
		- lista (str): Nome della lista ('mazzo', 'pescate', 'scarti', 'permanenti').
		Ritorna:
		- str: Stringa formattata con le carte o messaggio di lista vuota/non valida.
		'''
		target_lista_ref = None
		nome_lista = ""
		if lista == 'mazzo':
			target_lista_ref = self.carte
			nome_lista = "Mazzo Principale"
		elif lista == 'pescate':
			target_lista_ref = self.pescate
			nome_lista = "Carte Pescate"
		elif lista == 'scarti':
			target_lista_ref = self.scarti
			nome_lista = "Pila Scarti"
		elif lista == 'permanenti':
			target_lista_ref = self.scarti_permanenti
			nome_lista = "Scarti Permanenti"
		else:
			return "Lista non valida. Scegli tra: 'mazzo', 'pescate', 'scarti', 'permanenti'."
		if not target_lista_ref:
			return f"Nessuna carta nella lista '{nome_lista}'."
		# Usa la lista referenziata per ottenere le carte
		return f"{nome_lista} ({len(target_lista_ref)}): " + ", ".join([c.desc_breve for c in target_lista_ref])
