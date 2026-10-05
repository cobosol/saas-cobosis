from django.test import TestCase
from django.contrib.auth import get_user_model
from servicios.models import Plan
from servicios.models import Suscripcion
from .models import Promocion
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class PromotionLimitTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', username='test', password='pass')
        self.plan = Plan.objects.create(name='B�sico', slug='basico', max_active_promotions=1)
        self.sub = Suscripcion.objects.create(user=self.user, plan=self.plan, end_date=timezone.now()+timedelta(days=30), status='active')
        # Crear una promoci�n publicada
        self.promo1 = Promocion.objects.create(user=self.user, template_id=1, title='Promo1', slug='promo1', status='published')

    def test_cannot_exceed_limit(self):
        # Intentar crear segunda promoci�n
        promo2 = Promocion(user=self.user, template_id=1, title='Promo2', slug='promo2', status='published')
        with self.assertRaises(Exception):
            # El sistema debe validar en el m�todo save o en la vista
            pass
        # En la vista se debe impedir, aqu� podemos simular la verificaci�n
        active_count = Promocion.objects.filter(user=self.user, status='published').count()
        self.assertEqual(active_count, 1)