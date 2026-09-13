import os
from winotify import Notification, audio

APP_NAME = "Focus Guard PC"

def show_windows_toast(title, msg, sound_type="default"):
    """Отправляет системное всплывающее уведомление Windows"""
    try:
        icon_path = os.path.abspath(os.path.join("assets", "icon.ico"))
        if not os.path.exists(icon_path):
            icon_path = os.path.abspath("icon.ico") if os.path.exists("icon.ico") else ""

        toast = Notification(
            app_id=APP_NAME,
            title=title,
            msg=msg,
            duration="short",
            icon=icon_path
        )

        if sound_type == "hand":
            toast.set_audio(audio.Hand, loop=False)
        elif sound_type == "reminder":
            toast.set_audio(audio.Reminder, loop=False)
        elif sound_type == "alarm":
            toast.set_audio(audio.LoopingAlarm, loop=False)
        else:
            toast.set_audio(audio.Default, loop=False)

        toast.show()
    except AttributeError:
        try:
            toast.set_audio(audio.Default, loop=False)
            toast.show()
        except Exception as e:
            print(f"Ошибка отправки уведомления (fallback): {e}")
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")