# ------------------------------------------------------------------------------
# ------- Proyecto: Pictionary con Cámara (Procesamiento de Imagen en Tiempo Real)
# ------- Conceptos básicos de PDI -------------------------------------------
# ------- Por: Oscar David Mercado Gomez  oscar.mercado1@udea.edu.co -----------
#------------- Carlos Daniel Galvis Ramirez  daniel.galvis1@udea.edu.co ---------
# ------- Facultad de Ingeniería - Universidad de Antioquia -------------------
# ------- Curso: Procesamiento de Imágenes y Visión Artificial -----------------
# ------- V1 Octubre de 2025 ---------------------------------------------------
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# -- 1. Inicialización del sistema ---------------------------------------------
# ------------------------------------------------------------------------------

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import random
import time

# ------------------------------------------------------------------------------
# -- 2. Configuración general del entorno --------------------------------------
# ------------------------------------------------------------------------------

CAM_INDEX = 0 # Índice de la cámara (0 = cámara principal)
DRAW_COLOR = (0, 0, 255) # Color del trazo (rojo)
BRUSH_THICKNESS = 8 # Grosor del pincel
FRAME_W = 640 # Tamaño de ventana de cámara
FRAME_H = 480
TIMER_SECONDS = 60  # tiempo por ronda (0 para sin temporizador)
WORD_LIST = ["casa", "perro", "auto", "árbol", "sol", "manzana", "gato", "avión", "bicicleta", "estrella", "computador"]
# ------------------------------------------------------------------------------
# -- 3. Funciones auxiliares ---------------------------------------------------
# ------------------------------------------------------------------------------
def mask_word(word):
    """Devuelve la palabra oculta con guiones."""
    return ' '.join(['_' if c != ' ' else '/' for c in word])
# ------------------------------------------------------------------------------
# -- 4. Clase principal del programa (lógica del juego y procesamiento) --------
# ------------------------------------------------------------------------------
class PictionaryCamApp:
    def __init__(self, root):
                # ---------- Inicialización de la interfaz y cámara ----------
        self.root = root
        self.root.title("🎨 Pictionary con Cámara - Dibuja en el aire (objeto rojo)")
 # Configuración de la cámara
        self.vs = cv2.VideoCapture(CAM_INDEX, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else 0)
        self.vs.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        self.vs.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

        # Variables
        self.drawing_canvas = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
        self.prev_center = None
        self.current_word = ""
        self.start_time = None
        self.timer_enabled = TIMER_SECONDS > 0
        self.allow_drawing = False
        self.freeze_frame = None
        self.word_set = False

        # ----- INTERFAZ -----
        self.panel = tk.Label(root)
        self.panel.grid(row=0, column=0, columnspan=5, padx=5, pady=5)

        tk.Label(root, text="Palabra secreta (solo Jugador 1):").grid(row=1, column=0, sticky='e')
        self.word_entry = tk.Entry(root, show="•")
        self.word_entry.grid(row=1, column=1, sticky='w')

        self.set_btn = tk.Button(root, text="Fijar palabra", command=self.set_word)
        self.set_btn.grid(row=1, column=2, padx=4)

        self.clear_btn = tk.Button(root, text="Limpiar pizarra", command=self.clear_canvas)
        self.clear_btn.grid(row=1, column=3, padx=4)

        self.toggle_draw_btn = tk.Button(root, text="Iniciar dibujo", command=self.toggle_drawing)
        self.toggle_draw_btn.grid(row=1, column=4, padx=4)

        tk.Label(root, text="Adivina (Jugador 2):").grid(row=2, column=0, sticky='e')
        self.guess_entry = tk.Entry(root)
        self.guess_entry.grid(row=2, column=1, sticky='w')

        self.guess_btn = tk.Button(root, text="Intentar", command=self.try_guess, state="disabled")
        self.guess_btn.grid(row=2, column=2, padx=4)

        self.next_btn = tk.Button(root, text="Siguiente palabra", command=self.next_word, state="disabled")
        self.next_btn.grid(row=2, column=3, padx=4)

        self.unfreeze_btn = tk.Button(root, text="Reanudar cámara", command=self.unfreeze, state="disabled")
        self.unfreeze_btn.grid(row=2, column=4, padx=4)

        self.timer_label = tk.Label(root, text="")
        self.timer_label.grid(row=3, column=0, columnspan=5)

        self.word_label = tk.Label(root, text="", font=("Consolas", 16))
        self.word_label.grid(row=4, column=0, columnspan=5)

        self.update_frame()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)


    # ------------------------------------------------------------------------------
    # -- 5. Lógica del juego -------------------------------------------------------
    # ------------------------------------------------------------------------------
    def set_word(self):
        if self.word_set:
            messagebox.showinfo("Aviso", "Ya hay una palabra en juego. Termina la ronda antes de fijar otra.")
            return

        w = self.word_entry.get().strip().lower()
        if w == "":
            w = random.choice(WORD_LIST)
            self.word_entry.insert(0, w)

        self.current_word = w
        self.word_set = True
        self.clear_canvas()
        self.start_round_timer()

        # Mostrar información general (sin revelar la palabra)
        letras = len([c for c in w if c != ' '])
        espacios = w.count(' ')
        msg = f"Palabra secreta fijada ✅ ({letras} letras"
        if espacios > 0:
            msg += f" y {espacios} espacio{'s' if espacios > 1 else ''})"
        msg += ")"

        self.word_label.config(text=msg)
        self.toggle_draw_btn.config(state="normal")
        self.guess_btn.config(state="disabled")
        self.next_btn.config(state="disabled")

    def next_word(self):
        self.word_entry.delete(0, tk.END)
        self.word_label.config(text="")
        self.word_set = False
        self.clear_canvas()
        self.toggle_draw_btn.config(text="Iniciar dibujo", bg="SystemButtonFace")
        self.allow_drawing = False
        self.unfreeze_btn.config(state="disabled")

    def clear_canvas(self):
        self.drawing_canvas[:] = 0
        self.prev_center = None
        self.freeze_frame = None

    def toggle_drawing(self):
        if not self.word_set:
            messagebox.showinfo("Aviso", "Primero debes fijar una palabra secreta.")
            return

        self.allow_drawing = not self.allow_drawing
        if self.allow_drawing:
            self.toggle_draw_btn.config(text="Detener dibujo", bg="lightgreen")
            self.unfreeze_btn.config(state="disabled")
            self.freeze_frame = None
        else:
            self.toggle_draw_btn.config(text="Iniciar dibujo", bg="lightcoral")
            self.prev_center = None
            self.freeze_frame = self.current_display_frame.copy() if hasattr(self, 'current_display_frame') else None
            self.guess_btn.config(state="normal")
            self.unfreeze_btn.config(state="normal")
            self.word_label.config(text="Jugador 2: ¡Adivina la palabra!")

    def unfreeze(self):
        self.freeze_frame = None
        messagebox.showinfo("Cámara reanudada", "Cámara reactivada para continuar.")
        self.unfreeze_btn.config(state="disabled")

    def try_guess(self):
        guess = self.guess_entry.get().strip().lower()
        if guess == "":
            return
        if guess == self.current_word.lower():
            messagebox.showinfo("¡Correcto!", f"✅ ¡Acertaste! La palabra era: {self.current_word}")
            self.word_label.config(text=f"✅ Palabra: {self.current_word}")
            self.guess_btn.config(state="disabled")
            self.next_btn.config(state="normal")
        else:
            messagebox.showinfo("Incorrecto", "❌ No es correcto. Intenta de nuevo.")
        self.guess_entry.delete(0, tk.END)

    def start_round_timer(self):
        if self.timer_enabled:
            self.start_time = time.time()
        else:
            self.start_time = None

    # ------------------------------------------------------------------------------
    # -- 6. Procesamiento de imagen (detección del puntero rojo) -------------------
    # ------------------------------------------------------------------------------
    def detect_red_pointer(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower1 = np.array([0, 120, 70])
        upper1 = np.array([10, 255, 255])
        mask1 = cv2.inRange(hsv, lower1, upper1)
        lower2 = np.array([170, 120, 70])
        upper2 = np.array([180, 255, 255])
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, mask
        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < 200:
            return None, mask
        M = cv2.moments(c)
        if M["m00"] == 0:
            return None, mask
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return (cx, cy), mask

    # ------------------------------------------------------------------------------
    # -- 7. Captura y actualización del video -------------------------------------
    # ------------------------------------------------------------------------------

    def update_frame(self):
        if self.freeze_frame is not None:
            frame = self.freeze_frame
        else:
            ret, frame = self.vs.read()
            if not ret:
                self.root.after(30, self.update_frame)
                return

            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (FRAME_W, FRAME_H))

            center, mask = self.detect_red_pointer(frame)
            if center is not None and self.allow_drawing:
                if self.prev_center is None:
                    self.prev_center = center
                else:
                    cv2.line(self.drawing_canvas, self.prev_center, center, DRAW_COLOR, BRUSH_THICKNESS)
                    self.prev_center = center
            else:
                self.prev_center = None

            overlay = cv2.addWeighted(frame, 0.6, self.drawing_canvas, 0.4, 0)
            self.current_display_frame = overlay.copy()
            frame = overlay

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        imgtk = ImageTk.PhotoImage(image=img_pil)
        self.panel.imgtk = imgtk
        self.panel.configure(image=imgtk)

        if self.timer_enabled and self.start_time is not None:
            elapsed = int(time.time() - self.start_time)
            remaining = TIMER_SECONDS - elapsed
            if remaining < 0:
                self.timer_label.config(text="Tiempo: 0s — Fin de la ronda")
                messagebox.showinfo("Tiempo", "⏰ Se acabó el tiempo.")
                self.start_time = None
                self.word_label.config(text=f"La palabra era: {self.current_word}")
                self.guess_btn.config(state="disabled")
                self.next_btn.config(state="normal")
            else:
                self.timer_label.config(text=f"Tiempo restante: {remaining}s")
        else:
            self.timer_label.config(text="")

        self.root.after(16, self.update_frame)
    # ------------------------------------------------------------------------------
    # -- 8. Cierre del programa ----------------------------------------------------
    # ------------------------------------------------------------------------------

    def on_close(self):
        try:
            self.vs.release()
        except:
            pass
        self.root.destroy()

# ------------------------------------------------------------------------------
# -- 9. Ejecución principal -----------------------------------------------------
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = PictionaryCamApp(root)
    root.mainloop()
# ------------------------------------------------------------------------------
# ---------------------------  FIN DEL PROGRAMA ---------------------------------
# ------------------------------------------------------------------------------