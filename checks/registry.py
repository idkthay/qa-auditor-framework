from checks.analytics_check import (
    GoogleAnalyticsGa4Check,
)
from checks.base_check import BaseCheck
from checks.canonical_check import CanonicalMissingCheck
from checks.contact_check import (
    GoogleMapsCheck,
    InvalidHrefCheck,
    MailtoLinksCheck,
    TelephoneLinksCheck,
    WhatsappButtonCheck,
)
from checks.contact_format_check import (
    CepFormattingCheck,
    CpfCnpjFormattingCheck,
    EmailFormattingCheck,
    InputMaskCheck,
    PhoneFormattingCheck,
)
from checks.content_check import LoremIpsumCheck
from checks.form_check import (
    FormFieldIdentificationCheck,
    FormMethodCheck,
    FormPresenceCheck,
    FormSubmitButtonCheck,
    RecaptchaConflictCheck,
    RecaptchaPresenceCheck,
)
from checks.h1_check import (
    H1MissingCheck,
    H1MultipleCheck,
)
from checks.h2_check import H2MissingCheck
from checks.http_link_check import (
    HttpBrokenLinksCheck,
    HttpRedirectLinksCheck,
)
from checks.image_check import (
    BannersOver500KbCheck,
    ImagesBrokenCheck,
    ImagesEmptyAltCheck,
    ImagesMissingAltCheck,
    ImagesOver200KbCheck,
    ImagesSummaryCheck,
)
from checks.meta_description_check import (
    MetaDescriptionMissingCheck,
    MetaDescriptionOverCharactersCheck,
)
from checks.navigation_check import (
    ActiveMenuCheck,
    HeaderFooterMenuCheck,
    SitemapFooterCheck,
)
from checks.responsive_check import (
    ResponsiveDesktopCheck,
    ResponsiveMobile394Check,
    ResponsiveTablet768Check,
)
from checks.security_check import (
    HttpsUrlsCheck,
    MissingContentSecurityPolicyCheck,
    MissingHstsCheck,
    MissingReferrerPolicyCheck,
    MissingXContentTypeOptionsCheck,
    MissingXFrameOptionsCheck,
    MixedContentCheck,
)
from checks.site_files_check import (
    RobotsGlobalBlockCheck,
    RobotsSitemapDeclarationCheck,
    RobotsTxtCheck,
    SitemapXmlCheck,
)
from checks.status_check import (
    ResponseClientErrorCheck,
    ResponseRedirectionCheck,
    ResponseServerErrorCheck,
    ResponseSuccessCheck,
)
from checks.technical_seo_check import (
    CanonicalProtocolCheck,
    FaviconCheck,
    MetaRobotsFollowCheck,
    MetaRobotsIndexabilityCheck,
    MultipleCanonicalCheck,
    SelfCanonicalCheck,
    ViewportCheck,
)
from checks.title_check import (
    TitleMissingCheck,
    TitleOverCharactersCheck,
)
from checks.url_check import (
    UrlContainsSpaceCheck,
    UrlMultipleSlashesCheck,
    UrlNonAsciiCheck,
    UrlOverCharactersCheck,
    UrlUppercaseCheck,
)


def obter_checks() -> list[BaseCheck]:
    return [
        # Response Codes
        ResponseSuccessCheck(),
        ResponseRedirectionCheck(),
        ResponseClientErrorCheck(),
        ResponseServerErrorCheck(),

        # URLs
        UrlContainsSpaceCheck(),
        UrlMultipleSlashesCheck(),
        UrlNonAsciiCheck(),
        UrlOverCharactersCheck(),
        UrlUppercaseCheck(),

        # Titles
        TitleMissingCheck(),
        TitleOverCharactersCheck(),

        # Meta Description
        MetaDescriptionMissingCheck(),
        MetaDescriptionOverCharactersCheck(),

        # Headings
        H1MissingCheck(),
        H1MultipleCheck(),
        H2MissingCheck(),

        # Canonical básico
        CanonicalMissingCheck(),

        # SEO técnico
        MetaRobotsIndexabilityCheck(),
        MetaRobotsFollowCheck(),
        ViewportCheck(),
        FaviconCheck(),
        MultipleCanonicalCheck(),
        CanonicalProtocolCheck(),
        SelfCanonicalCheck(),

        # Analytics e ferramentas Google
        GoogleAnalyticsGa4Check(),

        # Robots e Sitemap
        RobotsTxtCheck(),
        RobotsGlobalBlockCheck(),
        RobotsSitemapDeclarationCheck(),
        SitemapXmlCheck(),

        # Conteúdo
        LoremIpsumCheck(),

        # Navegação
        HeaderFooterMenuCheck(),
        ActiveMenuCheck(),
        SitemapFooterCheck(),

        # Contatos
        WhatsappButtonCheck(),
        MailtoLinksCheck(),
        TelephoneLinksCheck(),
        GoogleMapsCheck(),
        PhoneFormattingCheck(),
        EmailFormattingCheck(),
        CepFormattingCheck(),
        CpfCnpjFormattingCheck(),

        # Links
        InvalidHrefCheck(),
        HttpBrokenLinksCheck(),
        HttpRedirectLinksCheck(),

        # Formulários
        FormPresenceCheck(),
        FormMethodCheck(),
        FormSubmitButtonCheck(),
        FormFieldIdentificationCheck(),
        RecaptchaPresenceCheck(),
        RecaptchaConflictCheck(),
        InputMaskCheck(),

        # Imagens
        ImagesMissingAltCheck(),
        ImagesEmptyAltCheck(),
        ImagesBrokenCheck(),
        ImagesOver200KbCheck(),
        BannersOver500KbCheck(),
        ImagesSummaryCheck(),

        # Layout e responsividade
        ResponsiveDesktopCheck(),
        ResponsiveMobile394Check(),
        ResponsiveTablet768Check(),

        # Segurança
        MixedContentCheck(),
        MissingHstsCheck(),
        HttpsUrlsCheck(),
        MissingXFrameOptionsCheck(),
        MissingReferrerPolicyCheck(),
        MissingContentSecurityPolicyCheck(),
        MissingXContentTypeOptionsCheck(),
    ]