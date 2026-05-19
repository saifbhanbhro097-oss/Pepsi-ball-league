from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.behaviors import ButtonBehavior
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.clock import Clock
from kivy.network.urlrequest import UrlRequest
import json
import base64

# FIX: Cross-platform platform utility instead of 'import webbrowser'
from kivy.utils import platform

Window.softinput_mode = "resize"

ONLINE_URL = "https://6a0c1ca85aa893e1015af370.mockapi.io/teams"
IMGBB_API_KEY = "eaabb841a057bd423251881cfe4296bd"

C_BG_DARK = (0.04, 0.05, 0.07, 1)       
C_CARD = (0.09, 0.11, 0.15, 0.95)       
C_TEXT_WHITE = (1, 1, 1, 1)             
C_MUTED = (0.5, 0.55, 0.62, 1)          
C_ACCENT_BLUE = (0.0, 0.5, 0.93, 1)     
C_SUCCESS_GREEN = (0.02, 0.72, 0.38, 1) 
C_ERROR_RED = (0.95, 0.22, 0.29, 1)     
C_LEAD_GOLD = (1.0, 0.73, 0.0, 1)       
C_LEAD_SILVER = (0.72, 0.76, 0.82, 1)   

REGISTERED_TEAMS_DATA = []

USER_TEAM = {
    "owner": "", "team_name": "", "mobile": "",
    "players": [""] * 8, "reserves": [""] * 3, 
    "photos": [""] * 11,  
    "is_registered": False, "m": 0, "w": 0, "l": 0, "pts": 0, "nrr": "0.000"
}

class CosmicScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*C_BG_DARK)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

class PatchedTextInput(TextInput):
    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if keycode[0] == 8 or keycode[1] == 'backspace':
            self.do_backspace()
            return True
        return super().keyboard_on_key_down(window, keycode, text, modifiers)

class UppercaseTextInput(PatchedTextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(text=self.on_text_change)

    def on_text_change(self, instance, value):
        if any(c.islower() for c in value):
            cursor = self.cursor
            self.text = value.upper()
            self.cursor = cursor

class LabeledInput(BoxLayout):
    def __init__(self, label_text, hint_text, force_caps=False, input_type='text', **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('spacing', dp(6))
        super().__init__(**kwargs)

        title = Label(text=label_text, font_size=sp(13), bold=True, color=C_TEXT_WHITE, halign='center')
        title.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.add_widget(title)

        input_box = BoxLayout(size_hint_y=None, height=dp(48), size_hint_x=None, width=dp(280), pos_hint={'center_x': 0.5})
        with input_box.canvas.before:
            Color(*C_CARD)
            self.input_bg = RoundedRectangle(pos=input_box.pos, size=input_box.size, radius=[dp(10)])
        input_box.bind(pos=lambda s, v: setattr(self.input_bg, 'pos', v), size=lambda s, v: setattr(self.input_bg, 'size', v))

        if force_caps:
            self.field = UppercaseTextInput(
                hint_text=hint_text, hint_text_color=(*C_MUTED[:3], 0.3),
                foreground_color=C_TEXT_WHITE, cursor_color=C_ACCENT_BLUE, multiline=False,
                font_size=sp(14), padding=[dp(12), dp(13), dp(12), dp(12)],
                background_normal='', background_active='', background_color=(0, 0, 0, 0),
                size_hint=(1, 1), write_tab=False, halign='center'
            )
        else:
            self.field = PatchedTextInput(
                hint_text=hint_text, hint_text_color=(*C_MUTED[:3], 0.3),
                foreground_color=C_TEXT_WHITE, cursor_color=C_ACCENT_BLUE, multiline=False,
                font_size=sp(14), padding=[dp(12), dp(13), dp(12), dp(12)],
                background_normal='', background_active='', background_color=(0, 0, 0, 0),
                size_hint=(1, 1), write_tab=False, halign='center'
            )
            
        if input_type == 'phone': 
            self.field.input_type = 'tel'

        input_box.add_widget(self.field)
        self.add_widget(input_box)

        self.error_lbl = Label(text='', font_size=sp(11), color=C_ERROR_RED, halign='center', size_hint_y=None, height=dp(0))
        self.error_lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.add_widget(self.error_lbl)
        self.height = dp(80)

    @property
    def text(self): return self.field.text
    @text.setter
    def text(self, value): self.field.text = value

    def show_error(self, msg):
        self.error_lbl.text = '[!] ' + msg
        self.error_lbl.height = dp(18)
        self.height = dp(98)

    def clear_error(self):
        self.error_lbl.text = ''
        self.error_lbl.height = dp(0)
        self.height = dp(80)

class MenuButton(ButtonBehavior, BoxLayout):
    def __init__(self, title, sub, color=C_ACCENT_BLUE, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(78))
        kwargs.setdefault('size_hint_x', None)
        kwargs.setdefault('width', dp(300))
        kwargs.setdefault('pos_hint', {'center_x': 0.5})
        kwargs.setdefault('padding', [dp(16), dp(12), dp(16), dp(12)])
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*C_CARD)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
            Color(*color[:3], 0.08)
            self.glow = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=self._refresh_ui, size=self._refresh_ui)
        
        lbl_m = Label(text=title, font_size=sp(15), bold=True, color=C_TEXT_WHITE, halign='center', valign='bottom')
        lbl_s = Label(text=sub, font_size=sp(11), color=C_MUTED, halign='center', valign='top')
        lbl_m.bind(size=lambda s,v: setattr(s,'text_size',v))
        lbl_s.bind(size=lambda s,v: setattr(s,'text_size',v))
        self.add_widget(lbl_m)
        self.add_widget(lbl_s)

    def _refresh_ui(self, *args):
        self.bg.pos = self.pos; self.bg.size = self.size
        self.glow.pos = self.pos; self.glow.size = self.size

class GridPlayerCard(BoxLayout):
    def __init__(self, role_label, role_color, upload_cb, is_input_mode=True, player_name="", card_height=dp(145), player_img="", **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', card_height)
        kwargs.setdefault('padding', dp(8))
        kwargs.setdefault('spacing', dp(6))
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(*C_CARD)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            Color(*role_color[:3], 0.3)
            self.border = RoundedRectangle(pos=(self.pos[0], self.pos[1]), size=(self.size[0], dp(3)), radius=[dp(0), dp(0), dp(12), dp(12)])
            
        self.bind(pos=self._update_shapes, size=self._update_shapes)

        self.tag_lbl = Label(text=role_label, font_size=sp(11), bold=True, color=role_color, size_hint_y=None, height=dp(14))
        self.add_widget(self.tag_lbl)

        self.img_frame = BoxLayout(size_hint=(1, 1))
        self.img = Image(source=player_img if (player_img and player_img.strip()) else '', fit_mode='contain')
        self.img_frame.add_widget(self.img)
        self.add_widget(self.img_frame)

        if is_input_mode:
            self.input_field = UppercaseTextInput(
                hint_text="ENTER NAME", hint_text_color=(1,1,1,0.15), text=player_name.upper(),
                foreground_color=C_TEXT_WHITE, background_color=(0,0,0,0.4),
                multiline=False, font_size=sp(11), padding=[dp(4), dp(6), dp(4), dp(4)], size_hint_y=None, height=dp(28), halign='center'
            )
            self.add_widget(self.input_field)

            self.upload_btn = Button(text='📷 PHOTO', font_size=sp(9), bold=True, size_hint_y=None, height=dp(22), background_color=C_ACCENT_BLUE)
            self.upload_btn.bind(on_press=upload_cb)
            self.add_widget(self.upload_btn)
        else:
            self.name_lbl = Label(text=player_name.upper() if player_name else "EMPTY SLOT", font_size=sp(12), bold=True, color=C_TEXT_WHITE, halign='center', size_hint_y=None, height=dp(20))
            self.name_lbl.bind(size=lambda s,v: setattr(s,'text_size',v))
            self.add_widget(self.name_lbl)

    def _update_shapes(self, instance, value):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.border.pos = self.pos
        self.border.size = (self.size[0], dp(3))

class RegistrationScreen(CosmicScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        outer_layout = BoxLayout(orientation='vertical', padding=dp(16))
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35))
        
        whatsapp_btn = Button(
            text="💬 ULFAT DAHRI", 
            font_size=sp(10), 
            bold=True,
            size_hint_x=None, 
            width=dp(110),
            background_normal='',
            background_color=C_SUCCESS_GREEN
        )
        whatsapp_btn.bind(on_press=self.open_whatsapp_contact)
        
        top_bar.add_widget(whatsapp_btn)
        top_bar.add_widget(BoxLayout(size_hint_x=1)) 
        outer_layout.add_widget(top_bar)
        
        center_box = BoxLayout(orientation='vertical', spacing=dp(16), size_hint_y=None, size_hint_x=None, width=dp(300))
        center_box.bind(minimum_height=center_box.setter('height'))
        center_box.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        
        center_box.add_widget(Label(text='PEPSI SUPER LEAGUE', font_size=sp(26), bold=True, color=C_ACCENT_BLUE, size_hint_y=None, height=dp(40), halign='center'))
        center_box.add_widget(Label(text='Online Franchise Registration', font_size=sp(12), color=C_MUTED, size_hint_y=None, height=dp(15), halign='center'))

        self.owner_input = LabeledInput(label_text='Captain / Owner Name', hint_text='', force_caps=True)
        self.mobile_input = LabeledInput(label_text='Mobile Contact Number', hint_text='', input_type='phone')
        self.team_input = LabeledInput(label_text='Official Team Name', hint_text='E.G., SUFI SMASHERS', force_caps=True)
        
        center_box.add_widget(self.owner_input)
        center_box.add_widget(self.mobile_input)
        center_box.add_widget(self.team_input)

        self.next_btn = Button(text='CONTINUE TO SQUAD MANAGER', font_size=sp(13), bold=True, size_hint_y=None, height=dp(50), background_color=C_ACCENT_BLUE)
        self.next_btn.bind(on_press=self.start_loading)
        center_box.add_widget(self.next_btn)
        
        outer_layout.add_widget(BoxLayout(size_hint_y=1))
        outer_layout.add_widget(center_box)
        outer_layout.add_widget(BoxLayout(size_hint_y=1))
        self.add_widget(outer_layout)

    def open_whatsapp_contact(self, instance):
        # FIX: Android System Native Intent mechanism instead of computer-based webbrowser
        whatsapp_url = "https://wa.me/923042458422"
        if platform == 'android':
            from jnius import cast, autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(whatsapp_url))
            currentActivity = PythonActivity.mActivity
            currentActivity.startActivity(intent)
        else:
            import webbrowser
            webbrowser.open(whatsapp_url)

    def start_loading(self, instance):
        self.next_btn.text = "PROCESSING..."
        self.next_btn.disabled = True
        Clock.schedule_once(self.verify_and_proceed, 0.1)

    def verify_and_proceed(self, dt):
        self.owner_input.clear_error()
        self.mobile_input.clear_error()
        self.team_input.clear_error()

        if not self.owner_input.text.strip():
            self.owner_input.show_error("Captain Name cannot be empty.")
            self.reset_button()
            return
        if not self.mobile_input.text.strip():
            self.mobile_input.show_error("Mobile Field required.")
            self.reset_button()
            return
        if not self.team_input.text.strip():
            self.team_input.show_error("Team Brand Identifier required.")
            self.reset_button()
            return

        USER_TEAM["owner"] = self.owner_input.text.strip().upper()
        USER_TEAM["mobile"] = self.mobile_input.text.strip()
        USER_TEAM["team_name"] = self.team_input.text.strip().upper()
        
        self.reset_button()
        self.manager.current = 'players_screen'

    def reset_button(self):
        self.next_btn.text = "CONTINUE TO SQUAD MANAGER"
        self.next_btn.disabled = False

class PlayersScreen(CosmicScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(12))
        layout.add_widget(Label(text='SQUAD MANAGER GRID', font_size=sp(20), bold=True, color=C_TEXT_WHITE, size_hint_y=None, height=dp(35), halign='center'))

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        container = BoxLayout(orientation='vertical', spacing=dp(16), size_hint_y=None)
        container.bind(minimum_height=container.setter('height'))

        self.cards_list = []
        leadership_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(185), spacing=dp(12))
        
        capt_card = GridPlayerCard(role_label="👑 [C] CAPTAIN", role_color=C_LEAD_GOLD, upload_cb=lambda x: self.pick_image(0), card_height=dp(185), size_hint_x=0.56)
        vc_card = GridPlayerCard(role_label="⭐ [VC] VICE ACT", role_color=C_LEAD_SILVER, upload_cb=lambda x: self.pick_image(1), card_height=dp(185), size_hint_x=0.44)
        
        leadership_box.add_widget(capt_card)
        leadership_box.add_widget(vc_card)
        self.cards_list.extend([capt_card, vc_card])
        container.add_widget(leadership_box)

        core_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        core_box.bind(minimum_height=core_box.setter('height'))
        core_box.add_widget(Label(text="CORE PLAYING SQUAD", font_size=sp(12), bold=True, color=C_ACCENT_BLUE, size_hint_y=None, height=dp(20)))

        core_grid = GridLayout(cols=3, spacing=dp(10), size_hint_y=None)
        core_grid.bind(minimum_height=core_grid.setter('height'))

        for i in range(1, 7):
            p_card = GridPlayerCard(role_label=f"PLAYER {i}", role_color=C_ACCENT_BLUE, upload_cb=lambda x, idx=1+i: self.pick_image(idx))
            core_grid.add_widget(p_card)
            self.cards_list.append(p_card)
            
        core_box.add_widget(core_grid)
        container.add_widget(core_box)

        reserve_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        reserve_box.bind(minimum_height=reserve_box.setter('height'))
        reserve_box.add_widget(Label(text="⚡  BENCH RESERVES  ⚡", font_size=sp(12), bold=True, color=C_MUTED, size_hint_y=None, height=dp(25)))

        reserve_grid = GridLayout(cols=3, spacing=dp(10), size_hint_y=None)
        reserve_grid.bind(minimum_height=reserve_grid.setter('height'))

        for i in range(1, 4):
            r_card = GridPlayerCard(role_label=f"RESERVE {i}", role_color=C_MUTED, upload_cb=lambda x, idx=7+i: self.pick_image(idx))
            reserve_grid.add_widget(r_card)
            self.cards_list.append(r_card)

        reserve_box.add_widget(reserve_grid)
        container.add_widget(reserve_box)

        scroll.add_widget(container)
        layout.add_widget(scroll)

        btn_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(12), size_hint_x=None, width=dp(320), pos_hint={'center_x': 0.5})
        back = Button(text='BACK', size_hint_x=0.3, background_color=(0.18, 0.20, 0.24, 1))
        back.bind(on_press=lambda x: setattr(self.manager, 'current', 'registration_screen'))
        
        self.save_btn = Button(text='SYNC SQUAD ONLINE', size_hint_x=0.7, background_color=C_SUCCESS_GREEN, bold=True)
        self.save_btn.bind(on_press=self.start_submit_loading)
        
        btn_box.add_widget(back)
        btn_box.add_widget(self.save_btn)
        layout.add_widget(btn_box)
        layout.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))
        self.add_widget(layout)

    def pick_image(self, index):
        chooser = FileChooserListView(filters=['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG'])
        top = BoxLayout(orientation='vertical', padding=dp(8))
        btn = Button(text='SELECT PHOTO', size_hint_y=None, height=dp(45), background_color=C_ACCENT_BLUE)
        top.add_widget(chooser)
        top.add_widget(btn)
        pop = Popup(title='Browse Gallery', content=top, size_hint=(0.9, 0.8))
        
        def confirm(x):
            if chooser.selection:
                btn.text = "UPLOADING TO CLOUD..."
                btn.disabled = True
                selected_photo = chooser.selection[0]
                
                try:
                    with open(selected_photo, "rb") as img_file:
                        b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    img_upload_url = f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}"
                    payload = f"image={b64_string}"
                    
                    def handle_img_success(req, result):
                        web_url = result.get('data', {}).get('url', '')
                        USER_TEAM["photos"][index] = web_url
                        self.cards_list[index].img.source = web_url
                        self.cards_list[index].img.reload()
                        pop.dismiss()

                    UrlRequest(img_upload_url, req_body=payload, method='POST', 
                               req_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                               on_success=handle_img_success, on_failure=lambda r, e: pop.dismiss())
                except Exception:
                    pop.dismiss()
                
        btn.bind(on_press=confirm)
        pop.open()

    def start_submit_loading(self, instance):
        self.save_btn.text = "UPLOADING SQUAD RECORD..."
        self.save_btn.disabled = True
        Clock.schedule_once(self.submit_squad, 0.1)

    def submit_squad(self, dt):
        USER_TEAM["owner"] = self.cards_list[0].input_field.text.strip().upper() or USER_TEAM["owner"]
        for i in range(1, 8):
            txt = self.cards_list[i].input_field.text.strip().upper()
            USER_TEAM["players"][i-1] = txt if txt else f"PLAYER {i}"
        for i in range(1, 4):
            txt = self.cards_list[7+i].input_field.text.strip().upper()
            USER_TEAM["reserves"][i-1] = txt if txt else f"RESERVE {i}"

        USER_TEAM["is_registered"] = True

        cloud_payload = json.dumps({
            "team_name": USER_TEAM["team_name"],
            "owner": USER_TEAM["owner"],
            "mobile": USER_TEAM["mobile"],
            "m": str(USER_TEAM["m"]), "w": str(USER_TEAM["w"]), "l": str(USER_TEAM["l"]),
            "pts": str(USER_TEAM["pts"]), "nrr": str(USER_TEAM["nrr"]),
            "players": USER_TEAM["players"],
            "reserves": USER_TEAM["reserves"],
            "photos": USER_TEAM["photos"]  
        })
        
        UrlRequest(ONLINE_URL, req_body=cloud_payload, method='POST', 
                   req_headers={'Content-Type': 'application/json'},
                   on_success=self.on_upload_done, on_failure=self.on_upload_done)

    def on_upload_done(self, request, result):
        self.save_btn.text = "SYNC SQUAD ONLINE"
        self.save_btn.disabled = False
        self.manager.current = 'main_menu_screen'

class MainMenuScreen(CosmicScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        outer_layout = BoxLayout(orientation='vertical', padding=dp(24))
        center_box = BoxLayout(orientation='vertical', spacing=dp(16), size_hint_y=None, size_hint_x=None, width=dp(300))
        center_box.bind(minimum_height=center_box.setter('height'))
        center_box.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        center_box.add_widget(Label(text='MAIN MENU', font_size=sp(24), bold=True, size_hint_y=None, height=dp(40), halign='center'))
        self.team_card = Label(text='Awaiting cloud sync parameters...', font_size=sp(13), size_hint_y=None, height=dp(45), color=C_MUTED, halign='center')
        center_box.add_widget(self.team_card)

        b1 = MenuButton(title='MY SQUAD', sub='View active squad line-up configuration.', color=C_ACCENT_BLUE)
        b2 = MenuButton(title='UPDATE ROSTER', sub='Modify your active players roster records.', color=C_LEAD_GOLD)
        b3 = MenuButton(title='ONLINE POINTS TABLE', sub='Explore details of competing franchises.', color=C_SUCCESS_GREEN)

        b1.bind(on_release=self.view_my_team_popup)
        b2.bind(on_release=lambda x: setattr(self.manager, 'current', 'players_screen'))
        b3.bind(on_release=lambda x: setattr(self.manager, 'current', 'teams_registry_screen'))

        center_box.add_widget(b1)
        center_box.add_widget(b2)
        center_box.add_widget(b3)
        
        outer_layout.add_widget(BoxLayout(size_hint_y=1))
        outer_layout.add_widget(center_box)
        outer_layout.add_widget(BoxLayout(size_hint_y=1))
        self.add_widget(outer_layout)

    def on_pre_enter(self):
        if USER_TEAM["is_registered"]:
            self.team_card.text = f"🛡️ ONLINE SQUAD ACTIVE: {USER_TEAM['team_name']}\n👑 CAPT: {USER_TEAM['owner']}"
        else:
            self.team_card.text = "Roster not synced yet.\nComplete registration steps."

    def view_my_team_popup(self, instance):
        if not USER_TEAM["is_registered"]:
            return
        mock_data = {
            "team_name": USER_TEAM["team_name"], "owner": USER_TEAM["owner"],
            "players": USER_TEAM["players"], "reserves": USER_TEAM["reserves"], "photos": USER_TEAM["photos"]
        }
        self.manager.get_screen('teams_registry_screen').show_squad_visual_popup(mock_data)

class TeamsRegistryScreen(CosmicScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        layout.add_widget(Label(text='GLOBAL POINTS TABLE', font_size=sp(20), bold=True, size_hint_y=None, height=dp(35), halign='center'))

        scroll = ScrollView(bar_width=dp(4))
        self.container = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, size_hint_x=None, width=dp(340))
        self.container.bind(minimum_height=self.container.setter('height'))
        self.container.pos_hint = {'center_x': 0.5}
        scroll.add_widget(self.container)
        layout.add_widget(scroll)

        back = Button(text='RETURN TO MENU', size_hint_y=None, height=dp(48), size_hint_x=None, width=dp(200), pos_hint={'center_x': 0.5}, background_color=C_ACCENT_BLUE)
        back.bind(on_press=lambda x: setattr(self.manager, 'current', 'main_menu_screen'))
        layout.add_widget(back)
        self.add_widget(layout)

    def on_pre_enter(self):
        self.container.clear_widgets()
        loading_lbl = Label(text="Downloading live server ranks...", color=C_MUTED, size_hint_y=None, height=dp(40))
        self.container.add_widget(loading_lbl)
        
        UrlRequest(ONLINE_URL, on_success=self.parse_online_data, on_failure=self.parse_online_data)

    def parse_online_data(self, request, result):
        self.container.clear_widgets()
        global REGISTERED_TEAMS_DATA
        REGISTERED_TEAMS_DATA = []

        if result and isinstance(result, list):
            REGISTERED_TEAMS_DATA = result

        REGISTERED_TEAMS_DATA = sorted(REGISTERED_TEAMS_DATA, key=lambda x: (int(x.get('pts', 0)), float(x.get('nrr', 0.0))), reverse=True)

        for rank, team in enumerate(REGISTERED_TEAMS_DATA, 1):
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(65), padding=dp(8), spacing=dp(8))
            with row.canvas.before:
                Color(*C_CARD)
                row.bg = RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(10)])
            row.bind(pos=lambda s,v: setattr(s.bg,'pos',v), size=lambda s,v: setattr(s.bg,'size',v))

            details = f"[b]{rank}. 🛡️ {team.get('team_name','Unknown').upper()}[/b]\n[color=8894a6]PTS: {team.get('pts',0)} | NRR: {team.get('nrr','0.000')} (W:{team.get('w',0)} L:{team.get('l',0)})[/color]"
            lbl = Label(text=details, markup=True, halign='left', size_hint_x=0.65, font_size=sp(12))
            lbl.bind(size=lambda s,v: setattr(s,'text_size',v))
            row.add_widget(lbl)

            view_btn = Button(text='VIEW SQUAD', size_hint_x=0.35, background_color=C_ACCENT_BLUE, font_size=sp(11), bold=True)
            view_btn.bind(on_press=lambda x, t=team: self.show_squad_visual_popup(t))
            row.add_widget(view_btn)
            self.container.add_widget(row)

    def show_squad_visual_popup(self, team_data):
        main_view = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(12))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        
        container_grid = BoxLayout(orientation='vertical', spacing=dp(14), size_hint_y=None)
        container_grid.bind(minimum_height=container_grid.setter('height'))

        raw_photos = team_data.get("photos", [])
        img_list = [""] * 11
        for i in range(11):
            if i < len(raw_photos):
                img_list[i] = raw_photos[i]

        lead_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(155), spacing=dp(10))
        lead_row.add_widget(GridPlayerCard(role_label="👑 CAPTAIN", role_color=C_LEAD_GOLD, upload_cb=None, is_input_mode=False, player_name=team_data.get('owner','').upper(), player_img=img_list[0], size_hint_x=0.56))
        
        v_name = ""
        if team_data.get('players') and len(team_data['players']) > 0:
            v_name = team_data['players'][0]
        lead_row.add_widget(GridPlayerCard(role_label="⭐ VICE CAPT", role_color=C_LEAD_SILVER, upload_cb=None, is_input_mode=False, player_name=v_name.upper(), player_img=img_list[1], size_hint_x=0.44))
        container_grid.add_widget(lead_row)

        core_grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None)
        core_grid.bind(minimum_height=core_grid.setter('height'))
        
        players_list = team_data.get('players', [])
        for idx, p in enumerate(players_list):
            if idx == 0 and len(players_list) > 1:
                continue
            core_grid.add_widget(GridPlayerCard(role_label="ACTIVE", role_color=C_ACCENT_BLUE, upload_cb=None, is_input_mode=False, player_name=p.upper(), player_img=img_list[2 + idx if (2 + idx) < len(img_list) else 2]))
        container_grid.add_widget(core_grid)

        bench_grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None)
        bench_grid.bind(minimum_height=bench_grid.setter('height'))
        for idx, r in enumerate(team_data.get('reserves', ['BENCH PLAYER']*3)):
            bench_grid.add_widget(GridPlayerCard(role_label="BENCH", role_color=C_MUTED, upload_cb=None, is_input_mode=False, player_name=r.upper(), player_img=img_list[8 + idx if (8 + idx) < len(img_list) else 8]))
        container_grid.add_widget(bench_grid)

        scroll.add_widget(container_grid)
        main_view.add_widget(scroll)

        pop = Popup(title=f"{team_data.get('team_name','Roster').upper()} Sheet", content=main_view, size_hint=(0.95, 0.88))
        close_btn = Button(text='CLOSE ROSTER VIEW', size_hint_y=None, height=dp(44), background_color=C_ERROR_RED, bold=True)
        close_btn.bind(on_press=pop.dismiss)
        main_view.add_widget(close_btn)
        pop.open()

class PepsiSuperLeagueApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(RegistrationScreen(name='registration_screen'))
        sm.add_widget(PlayersScreen(name='players_screen'))
        sm.add_widget(MainMenuScreen(name='main_menu_screen'))
        sm.add_widget(TeamsRegistryScreen(name='teams_registry_screen'))
        return sm

if __name__ == '__main__':
    PepsiSuperLeagueApp().run()

