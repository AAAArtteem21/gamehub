
import datetime as dt
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.lfg.models import LFGPost, LFGResponse

pytestmark = pytest.mark.django_db


# ---------- fixtures ----------

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username='author', password='pass12345')


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(username='responder', password='pass12345')


@pytest.fixture
def third_user(django_user_model):
    return django_user_model.objects.create_user(username='third', password='pass12345')


def make_post(author, **kwargs):
    defaults = dict(
        game='CS2',
        datetime=timezone.now() + dt.timedelta(hours=2),
        description='ищу тиммейта',
        contact='disc#1234',
        status='open',
    )
    defaults.update(kwargs)
    return LFGPost.objects.create(author=author, **defaults)


def post_list_url():
    return reverse('lfgpost-list')


def post_detail_url(pk):
    return reverse('lfgpost-detail', args=[pk])


def post_close_url(pk):
    return reverse('lfgpost-close', args=[pk])


def response_list_url():
    return reverse('lfgresponse-list')


# ---------- LFGPostViewSet: get_queryset / filtering ----------

class TestPostListFiltering:

    def test_default_shows_only_open(self, api_client, user):
        make_post(user, status='open')
        make_post(user, status='closed')
        resp = api_client.get(post_list_url())
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results'] if 'results' in resp.data else resp.data) == 1

    def test_explicit_status_filter_overrides_default(self, api_client, user):
        make_post(user, status='closed')
        resp = api_client.get(post_list_url(), {'status': 'closed'})
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert len(data) == 1

    def test_invalid_status_value_returns_empty_not_error(self, api_client, user):
        # Текущее поведение: произвольная строка в status тихо фильтрует в пустоту.
        # Возможно, стоит валидировать значение через ChoiceFilter вместо
        # query_params.get, но пока фиксируем как есть.
        make_post(user, status='open')
        resp = api_client.get(post_list_url(), {'status': 'not_a_real_status'})
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert resp.status_code == status.HTTP_200_OK
        assert len(data) == 0

    def test_game_filter_case_insensitive(self, api_client, user):
        make_post(user, game='Dota 2')
        resp = api_client.get(post_list_url(), {'game': 'dota 2'})
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert len(data) == 1


# ---------- responses_count_annotated fallback bug ----------

class TestResponsesCountAnnotation:

    def test_annotated_count_used_without_extra_queries(self, api_client, user, django_assert_num_queries):
        """
        Регрессия: если кто-то снова напишет
            getattr(obj, 'responses_count_annotated', None) or obj.responses.count()
        вместо явной проверки на None — на постах с 0 откликов появится
        лишний SELECT на каждый пост. Фиксируем текущее (верное) число запросов.
        """
        make_post(user)
        make_post(user)
        with django_assert_num_queries(1):
            resp = api_client.get(post_list_url())
        assert resp.status_code == status.HTTP_200_OK

    def test_nonzero_responses_count_is_correct(self, api_client, user, other_user):
        post = make_post(user)
        LFGResponse.objects.create(post=post, user=other_user)
        resp = api_client.get(post_detail_url(post.id))
        assert resp.data['responses_count'] == 1


# ---------- create / validators ----------

class TestPostCreate:

    def test_requires_auth(self, api_client):
        resp = api_client.post(post_list_url(), {
            'game': 'CS2', 'datetime': timezone.now() + dt.timedelta(hours=1),
            'contact': 'disc#1',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_success(self, api_client, user):
        api_client.force_authenticate(user)
        resp = api_client.post(post_list_url(), {
            'game': 'CS2',
            'datetime': (timezone.now() + dt.timedelta(hours=1)).isoformat(),
            'description': 'go',
            'contact': 'disc#1234',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['status'] == 'open'
        assert LFGPost.objects.get().author_id == user.id

    def test_past_datetime_rejected(self, api_client, user):
        api_client.force_authenticate(user)
        resp = api_client.post(post_list_url(), {
            'game': 'CS2',
            'datetime': (timezone.now() - dt.timedelta(hours=1)).isoformat(),
            'contact': 'disc#1234',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'datetime' in resp.data

    def test_game_too_short_rejected(self, api_client, user):
        api_client.force_authenticate(user)
        resp = api_client.post(post_list_url(), {
            'game': 'A',
            'datetime': (timezone.now() + dt.timedelta(hours=1)).isoformat(),
            'contact': 'disc#1234',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'game' in resp.data

    def test_contact_too_short_rejected(self, api_client, user):
        api_client.force_authenticate(user)
        resp = api_client.post(post_list_url(), {
            'game': 'CS2',
            'datetime': (timezone.now() + dt.timedelta(hours=1)).isoformat(),
            'contact': 'ab',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'contact' in resp.data

    def test_description_too_long_rejected(self, api_client, user):
        api_client.force_authenticate(user)
        resp = api_client.post(post_list_url(), {
            'game': 'CS2',
            'datetime': (timezone.now() + dt.timedelta(hours=1)).isoformat(),
            'description': 'x' * 301,
            'contact': 'disc#1234',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'description' in resp.data

    @patch('apps.lfg.serializers.validate_no_profanity')
    def test_profanity_check_called_for_game_and_description(self, mocked_validator, api_client, user):
        api_client.force_authenticate(user)
        api_client.post(post_list_url(), {
            'game': 'CS2',
            'datetime': (timezone.now() + dt.timedelta(hours=1)).isoformat(),
            'description': 'normal text',
            'contact': 'disc#1234',
        })
        assert mocked_validator.call_count == 2

    def test_ratelimit_blocks_after_five_per_hour(self, api_client, user, settings):
        settings.RATELIMIT_ENABLE = True
        api_client.force_authenticate(user)
        payload = lambda i: {
            'game': f'Game{i}',
            'datetime': (timezone.now() + dt.timedelta(hours=1)).isoformat(),
            'contact': 'disc#1234',
        }
        for i in range(5):
            resp = api_client.post(post_list_url(), payload(i))
            assert resp.status_code == status.HTTP_201_CREATED
        resp = api_client.post(post_list_url(), payload(99))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------- close action ----------

class TestClosePost:

    def test_author_can_close(self, api_client, user):
        post = make_post(user)
        api_client.force_authenticate(user)
        resp = api_client.post(post_close_url(post.id))
        assert resp.status_code == status.HTTP_200_OK
        post.refresh_from_db()
        assert post.status == 'closed'

    def test_non_author_cannot_close(self, api_client, user, other_user):
        post = make_post(user)
        api_client.force_authenticate(other_user)
        resp = api_client.post(post_close_url(post.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        post.refresh_from_db()
        assert post.status == 'open'

    def test_anonymous_cannot_close(self, api_client, user):
        post = make_post(user)
        resp = api_client.post(post_close_url(post.id))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_close_nonexistent_post_404(self, api_client, user):
        api_client.force_authenticate(user)
        resp = api_client.post(post_close_url(999999))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------- LFGResponseViewSet ----------

class TestResponseCreate:

    def test_requires_auth(self, api_client, user):
        post = make_post(user)
        resp = api_client.post(response_list_url(), {'post': post.id})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_success(self, api_client, user, other_user):
        post = make_post(user)
        api_client.force_authenticate(other_user)
        resp = api_client.post(response_list_url(), {'post': post.id})
        assert resp.status_code == status.HTTP_201_CREATED
        assert LFGResponse.objects.filter(post=post, user=other_user).exists()

    def test_duplicate_response_rejected(self, api_client, user, other_user):
        post = make_post(user)
        LFGResponse.objects.create(post=post, user=other_user)
        api_client.force_authenticate(other_user)
        resp = api_client.post(response_list_url(), {'post': post.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_author_cannot_respond_to_own_post(self, api_client, user):
        post = make_post(user)
        api_client.force_authenticate(user)
        resp = api_client.post(response_list_url(), {'post': post.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_respond_to_closed_post(self, api_client, user, other_user):
        post = make_post(user, status='closed')
        api_client.force_authenticate(other_user)
        resp = api_client.post(response_list_url(), {'post': post.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_filtered_by_post(self, api_client, user, other_user, third_user):
        post_a = make_post(user)
        post_b = make_post(user)
        LFGResponse.objects.create(post=post_a, user=other_user)
        LFGResponse.objects.create(post=post_b, user=third_user)
        api_client.force_authenticate(other_user)
        resp = api_client.get(response_list_url(), {'post': post_a.id})
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert len(data) == 1
        assert data[0]['post'] == post_a.id

    def test_list_without_post_filter_leaks_all_responses(self, api_client, user, other_user, third_user):
        """
        Баг/дизайн-вопрос: get_queryset без ?post= отдаёт ВСЕ отклики
        всех пользователей на все посты. Любой авторизованный юзер видит,
        кто на что откликался — включая чужие пары автор/отклик.
        Если это не задумано — нужно либо фильтровать по
        request.user (свои отклики + отклики на свои посты),
        либо требовать post обязательным параметром.
        """
        post = make_post(user)
        LFGResponse.objects.create(post=post, user=other_user)
        api_client.force_authenticate(third_user)  # третий, посторонний, юзер
        resp = api_client.get(response_list_url())
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert len(data) == 1  # текущее поведение — видно чужой отклик


class TestResponseOwnershipGap:

    def test_stranger_cannot_delete_someone_elses_response(self, api_client, user, other_user, third_user):
        post = make_post(user)
        resp_obj = LFGResponse.objects.create(post=post, user=other_user)
        api_client.force_authenticate(third_user)
        resp = api_client.delete(reverse('lfgresponse-detail', args=[resp_obj.id]))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert LFGResponse.objects.filter(id=resp_obj.id).exists()

    def test_owner_can_delete_own_response(self, api_client, user, other_user):
        post = make_post(user)
        resp_obj = LFGResponse.objects.create(post=post, user=other_user)
        api_client.force_authenticate(other_user)
        resp = api_client.delete(reverse('lfgresponse-detail', args=[resp_obj.id]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not LFGResponse.objects.filter(id=resp_obj.id).exists()